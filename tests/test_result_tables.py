import unittest
from datetime import datetime

from foosbam import create_app, db
from foosbam.models import Match, Result, User


class TestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    WTF_CSRF_ENABLED = False


class ResultTableRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

        self.players = {}
        for username in ('alice', 'bob', 'carol', 'dave', 'erin'):
            player = User(username=username, email=f'{username}@example.com')
            player.set_password('password')
            db.session.add(player)
            self.players[username] = player
        db.session.flush()

        self.matches = [
            self.add_match(2024, datetime(2024, 1, 1), 'alice', 'bob', 'carol', 'dave', 10, 8),
            self.add_match(2025, datetime(2025, 1, 1), 'erin', 'bob', 'carol', 'dave', 8, 10),
            self.add_match(2025, datetime(2025, 2, 1), 'alice', 'bob', 'erin', 'dave', 12, 10),
            self.add_match(2024, datetime(2024, 3, 1), 'carol', 'dave', 'erin', 'bob', 10, 12),
            self.add_match(2025, datetime(2025, 4, 1), 'erin', 'alice', 'carol', 'dave', 12, 10),
        ]
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.players['alice'].id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def add_match(self, season, played_at, att_black, def_black, att_white, def_white,
                  score_black, score_white):
        match = Match(
            season=season,
            played_at=played_at,
            att_black=self.players[att_black].id,
            def_black=self.players[def_black].id,
            att_white=self.players[att_white].id,
            def_white=self.players[def_white].id,
        )
        db.session.add(match)
        db.session.flush()
        db.session.add(Result(
            match_id=match.id,
            created_by=self.players['alice'].id,
            status='Approved',
            score_black=score_black,
            score_white=score_white,
            klinker_att_black=0,
            klinker_att_white=0,
            klinker_def_black=0,
            klinker_def_white=0,
            keeper_black=0,
            keeper_white=0,
        ))
        return match

    def test_default_order_and_page_boundaries(self):
        response = self.client.get('/show_results?per_page=2')
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'match/{self.matches[-1].id}', body)
        self.assertIn(f'match/{self.matches[2].id}', body)
        self.assertNotIn(f'match/{self.matches[0].id}', body)
        self.assertIn('Page 1 of 3 (5 matches)', body)
        self.assertLess(body.index(f'match/{self.matches[-1].id}'), body.index(f'match/{self.matches[2].id}'))

    def test_season_and_player_search_filters(self):
        response = self.client.get('/show_results?season=2024&q=alice')
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'match/{self.matches[0].id}', body)
        self.assertNotIn(f'match/{self.matches[3].id}', body)
        self.assertIn('1 matches', body)

    def test_sorting_and_invalid_parameters_are_bounded(self):
        response = self.client.get('/show_results?sort=score_black&direction=asc&per_page=25')
        body = response.get_data(as_text=True)
        self.assertLess(body.index(f'match/{self.matches[1].id}'), body.index(f'match/{self.matches[0].id}'))

        invalid = self.client.get('/show_results?page=-2&per_page=999&sort=invalid&direction=sideways')
        invalid_body = invalid.get_data(as_text=True)
        self.assertEqual(invalid.status_code, 200)
        self.assertIn('Page 1 of 1 (5 matches)', invalid_body)
        self.assertIn('100 per page', invalid_body)

    def test_player_history_remains_scoped_and_filterable(self):
        alice_id = self.players['alice'].id
        response = self.client.get(f'/user/{alice_id}?season=2025&q=erin&per_page=1')
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'match/{self.matches[4].id}', body)
        self.assertNotIn(f'match/{self.matches[3].id}', body)
        self.assertIn('Page 1 of 2 (2 matches)', body)

    def test_empty_search_renders_cleanly(self):
        response = self.client.get('/show_results?q=not-a-player')
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('No results found.', body)
        self.assertIn('Page 1 of 1 (0 matches)', body)

    def test_add_result_rejects_invalid_scores(self):
        players = list(self.players.values())
        base_form = {
            'date': '2025-06-01',
            'time': '12:34',
            'att_black': str(players[0].id),
            'def_black': str(players[1].id),
            'att_white': str(players[2].id),
            'def_white': str(players[3].id),
            'klinker_att_black': '0',
            'klinker_def_black': '0',
            'klinker_att_white': '0',
            'klinker_def_white': '0',
            'keeper_black': '0',
            'keeper_white': '0',
        }

        for score_black, score_white in (('10', '7'), ('9', '7')):
            with self.subTest(score_black=score_black, score_white=score_white):
                response = self.client.post(
                    '/add_result',
                    data={
                        **base_form,
                        'score_black': score_black,
                        'score_white': score_white,
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    'Scores must differ by exactly 2 points',
                    response.get_data(as_text=True),
                )
                self.assertEqual(Match.query.count(), 5)


if __name__ == '__main__':
    unittest.main()