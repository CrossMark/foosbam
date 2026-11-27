import re
import unittest
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import parse_qs, urlsplit

from foosbam import create_app, db
from foosbam.core.statistics import get_leaderboards, get_player_roles
from foosbam.models import Match, Result, User


class TestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True


class StatisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)

    def setUp(self):
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.players = {}
        for name in ('alice', 'bob', 'carol', 'dave'):
            player = User(username=name, email=f'{name}@example.com', password_hash='unused')
            db.session.add(player)
            self.players[name] = player
        db.session.flush()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.players['alice'].id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def add_match(self, number, players, scores=(10, 8), klinkers=(1, 2, 3, 4), keepers=(5, 6)):
        match = Match(
            played_at=datetime(2024, 1, 1) + timedelta(days=number),
            season=1,
            att_black=self.players[players[0]].id,
            def_black=self.players[players[1]].id,
            att_white=self.players[players[2]].id,
            def_white=self.players[players[3]].id,
        )
        db.session.add(match)
        db.session.flush()
        db.session.add(Result(
            match_id=match.id, created_by=self.players['alice'].id, status='Pending',
            score_black=scores[0], score_white=scores[1],
            klinker_att_black=klinkers[0], klinker_def_black=klinkers[1],
            klinker_att_white=klinkers[2], klinker_def_white=klinkers[3],
            keeper_black=keepers[0], keeper_white=keepers[1],
        ))

    def boards(self, **filters):
        searches = dict.fromkeys(('rivalry', 'partnership', 'keeper', 'klinker', 'attacker', 'defender'), '')
        searches.update(filters)
        return get_leaderboards(searches)

    def test_wins_partnership_roles_and_recorded_totals(self):
        self.add_match(0, ('alice', 'bob', 'carol', 'dave'))
        self.add_match(1, ('carol', 'dave', 'bob', 'alice'), (8, 10))
        self.add_match(2, ('alice', 'carol', 'bob', 'dave'), (8, 10))
        self.add_match(3, ('alice', 'bob', 'carol', 'dave'), (10, 10))
        db.session.commit()

        boards = self.boards(rivalry='ALICE', partnership='bob', keeper='alice',
                             klinker='alice', attacker='alice', defender='alice')
        self.assertEqual(
            [(row['players'][1]['name'], row['wins'], row['matches']) for row in boards['rivalry']],
            [('Dave', 2, 4), ('Carol', 2, 3), ('Bob', 0, 1)],
        )
        pair = next(row for row in boards['partnership'] if
                    {p['name'] for p in row['players']} == {'Alice', 'Bob'})
        self.assertEqual((pair['wins'], pair['matches']), (2, 3))
        self.assertEqual(boards['keeper'][0]['total'], 6)
        self.assertEqual(boards['klinker'][0]['total'], 7)
        self.assertEqual((boards['attacker'][0]['wins'], boards['attacker'][0]['matches']), (1, 3))
        self.assertEqual((boards['defender'][0]['wins'], boards['defender'][0]['matches']), (1, 1))
        roles = get_player_roles(self.players['alice'].id)
        self.assertEqual(roles['attacker'], {'wins': 1, 'matches': 3})
        self.assertEqual(roles['defender'], {'wins': 1, 'matches': 1})
        profile = self.client.get(f"/user/{self.players['alice'].id}").get_data(as_text=True)
        self.assertIn('Performance by role', profile)
        self.assertIn('33.3%', profile)
        self.assertIn('100.0%', profile)

    def test_rankings_and_search_include_all_results(self):
        for index in range(12):
            name = f'player{index:02}'
            self.players[name] = User(username=name, email=f'{name}@example.com', password_hash='unused')
            db.session.add(self.players[name])
            db.session.flush()
            self.add_match(index, (name, 'bob', 'carol', 'dave'), keepers=(index, 0))
        db.session.commit()
        boards = self.boards()
        self.assertGreater(len(boards['rivalry']), 10)
        self.assertGreater(len(boards['partnership']), 10)
        self.assertGreater(len(boards['klinker']), 10)
        self.assertGreater(len(boards['attacker']), 10)
        boards = self.boards(rivalry='player11', partnership='player11', klinker='player11',
                             attacker='player11', keeper='missing', defender='missing')
        for category in ('rivalry', 'partnership', 'klinker', 'attacker'):
            self.assertTrue(boards[category])
            self.assertTrue(any(p['name'] == 'Player11' for p in boards[category][0]['players']))
        self.assertEqual(boards['keeper'], [])
        self.assertEqual(boards['defender'], [])

    def test_independent_pagination_and_search(self):
        for index in range(12):
            name = f'player{index:02}'
            self.players[name] = User(username=name, email=f'{name}@example.com', password_hash='unused')
            db.session.add(self.players[name])
            db.session.flush()
            self.add_match(index, (name, 'bob', 'carol', 'dave'))
            self.add_match(index + 12, ('alice', name, 'bob', 'carol'))
        db.session.commit()

        def section(body, category):
            return re.search(rf'<section class="block" id="{category}">(.*?)</section>', body, re.S).group(1)

        for category in ('rivalry', 'partnership', 'keeper', 'klinker', 'attacker', 'defender'):
            with self.subTest(category=category):
                first = section(self.client.get(f'/statistics?{category}=player').get_data(as_text=True), category)
                self.assertIn('Page 1 of ', first)
                self.assertIn('<th scope="row">10</th>', first)
                self.assertNotIn('<th scope="row">11</th>', first)
                link = unescape(re.search(r'<a class="pagination-next" href="([^"]+)"', first).group(1))
                second = section(self.client.get(link).get_data(as_text=True), category)
                self.assertIn('Page 2 of ', second)
                self.assertIn('<th scope="row">11</th>', second)
                self.assertIn('pagination-previous', second)
                self.assertEqual(parse_qs(urlsplit(link).query)[category], ['player'])

        body = self.client.get('/statistics?attacker=player&attacker_page=2&keeper=player&keeper_page=2').get_data(as_text=True)
        attacker = section(body, 'attacker')
        self.assertIn('name="keeper_page" value="2"', attacker)
        self.assertNotIn('name="attacker_page"', attacker)
        link = unescape(re.search(r'<a class="pagination-previous" href="([^"]+)"', attacker).group(1))
        query = parse_qs(urlsplit(link).query)
        self.assertEqual(query['keeper_page'], ['2'])
        self.assertEqual(query['keeper'], ['player'])
        self.assertEqual(query['attacker_page'], ['1'])

        filtered = section(self.client.get('/statistics?attacker=player11&attacker_page=2').get_data(as_text=True), 'attacker')
        self.assertIn('Page 1 of 1 (1 results)', filtered)
        self.assertIn('Player11', filtered)
        invalid = self.client.get('/statistics?attacker_page=invalid&keeper_page=-1&defender_page=999').get_data(as_text=True)
        self.assertIn('Page 1 of 2', section(invalid, 'attacker'))
        self.assertIn('Page 1 of 2', section(invalid, 'keeper'))
        self.assertIn('Page 2 of 2', section(invalid, 'defender'))

    def test_page_searches_are_independent_and_preserved(self):
        self.add_match(0, ('alice', 'bob', 'carol', 'dave'))
        db.session.commit()
        response = self.client.get('/statistics?rivalry=alice&partnership=BOB&keeper=missing')
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/statistics"', body)
        self.assertIn('name="rivalry" value="alice"', body)
        self.assertIn('name="partnership" value="BOB"', body)
        keeper_section = re.search(r'<section class="block" id="keeper">(.*?)</section>', body, re.S).group(1)
        self.assertIn('No results found.', keeper_section)
        rivalry_section = re.search(r'<section class="block" id="rivalry">(.*?)</section>', body, re.S).group(1)
        self.assertIn('Alice', rivalry_section)
        self.assertIn('Carol', rivalry_section)
        self.assertNotIn('Latest match', body)

    def test_empty_and_login_required(self):
        self.assertIn('No results found.', self.client.get('/statistics').get_data(as_text=True))
        profile = self.client.get(f"/user/{self.players['alice'].id}").get_data(as_text=True)
        self.assertIn('Performance by role', profile)
        self.assertNotIn('0.0%', profile)
        self.client.get('/auth/logout')
        self.assertEqual(self.client.get('/statistics').status_code, 302)


if __name__ == '__main__':
    unittest.main()
