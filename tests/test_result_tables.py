import unittest
from datetime import datetime
import re
from unittest.mock import patch

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

    def test_kruipen_rows_are_highlighted_in_both_result_tables(self):
        zero_score_match = self.add_match(
            2025, datetime(2025, 5, 1), 'alice', 'bob', 'carol', 'dave', 0, 10
        )
        negative_score_match = self.add_match(
            2025, datetime(2025, 5, 2), 'erin', 'bob', 'alice', 'dave', 10, -1
        )
        db.session.commit()

        for url in ('/show_results?per_page=100', f'/user/{self.players["alice"].id}?per_page=100'):
            with self.subTest(url=url):
                response = self.client.get(url)
                body = response.get_data(as_text=True)

                self.assertEqual(response.status_code, 200)
                for match in (zero_score_match, negative_score_match):
                    row = self._result_row(body, match.id)
                    self.assertIn('has-background-danger-light', row)

                positive_row = self._result_row(body, self.matches[0].id)
                self.assertNotIn('has-background-danger-light', positive_row)

    def test_kruipen_filter_limits_results_and_persists_across_pages(self):
        zero_score_match = self.add_match(
            2025, datetime(2025, 5, 1), 'alice', 'bob', 'carol', 'dave', 0, 10
        )
        negative_score_match = self.add_match(
            2025, datetime(2025, 5, 2), 'erin', 'bob', 'alice', 'dave', 10, -1
        )
        db.session.commit()

        first_page = self.client.get('/show_results?kruipen=only&per_page=1')
        first_body = first_page.get_data(as_text=True)
        self.assertEqual(first_page.status_code, 200)
        self.assertIn(f'match/{negative_score_match.id}', first_body)
        self.assertNotIn(f'match/{zero_score_match.id}', first_body)
        self.assertIn('Page 1 of 2 (2 matches)', first_body)
        self.assertIn('class="checkbox kruipen-filter"', first_body)
        self.assertIn('name="kruipen" value="only" checked', first_body)
        next_link = re.search(r'<a class="pagination-next" href="([^"]+)"', first_body)
        self.assertIsNotNone(next_link)
        self.assertIn('kruipen=only', next_link.group(1))

        second_page = self.client.get('/show_results?kruipen=only&per_page=1&page=2')
        self.assertIn(f'match/{zero_score_match.id}', second_page.get_data(as_text=True))

        all_matches = self.client.get('/show_results?kruipen=all&per_page=100')
        all_body = all_matches.get_data(as_text=True)
        self.assertIn(f'match/{self.matches[0].id}', all_body)
        self.assertIn(f'match/{zero_score_match.id}', all_body)
        self.assertIn(f'match/{negative_score_match.id}', all_body)
        self.assertIn('Page 1 of 1 (7 matches)', all_body)
        self.assertNotIn('name="kruipen" value="only" checked', all_body)

        player_history = self.client.get(
            f'/user/{self.players["alice"].id}?kruipen=only&per_page=100'
        )
        player_body = player_history.get_data(as_text=True)
        self.assertIn(f'match/{zero_score_match.id}', player_body)
        self.assertIn(f'match/{negative_score_match.id}', player_body)
        self.assertNotIn(f'match/{self.matches[0].id}', player_body)
        self.assertIn('class="checkbox kruipen-filter"', player_body)

    def _result_row(self, body, match_id):
        for row in re.findall(r'<tr\b[^>]*>.*?</tr>', body, flags=re.DOTALL):
            if f'href="/match/{match_id}"' in row:
                return row
        self.fail(f'No result row found for match {match_id}')

    def test_empty_search_renders_cleanly(self):
        response = self.client.get('/show_results?q=not-a-player')
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('No results found.', body)
        self.assertIn('Page 1 of 1 (0 matches)', body)

    def test_add_result_validates_winner_and_minimum_score_margin(self):
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

        with patch(
            'foosbam.core.routes.elo.construct_dataframe',
            return_value={'rating_obj': []},
        ):
            valid_response = self.client.post(
                '/add_result',
                data={**base_form, 'score_black': '10', 'score_white': '7'},
            )
        self.assertEqual(valid_response.status_code, 302)
        Result.query.filter_by(score_black=10, score_white=7).one()
        self.assertEqual(Match.query.count(), 6)

        for score_black, score_white in (('10', '9'), ('9', '7')):
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
                    'Scores must differ by at least 2 points',
                    response.get_data(as_text=True),
                )
                self.assertEqual(Match.query.count(), 6)


if __name__ == '__main__':
    unittest.main()