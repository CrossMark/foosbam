import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from foosbam import create_app, db, mail
from foosbam.core import details
from foosbam.email import send_email, send_password_reset
from foosbam.models import Match, Rating, Result, User


class TestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


class AppWorkflowTests(unittest.TestCase):
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
        for player in self.players.values():
            db.session.add(Rating(
                user_id=player.id, match_id=None, since=datetime(1900, 1, 1),
                season=0, previous_rating=None, rating=1500,
                previous_rating_season=None, rating_season=1500,
            ))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def log_in(self, username='alice', password='password'):
        response = self.client.post('/auth/login', data={
            'username': username, 'password': password,
        })
        self.assertEqual(response.status_code, 302)

    def match_data(self, timestamp='2025-06-01', at='12:34', **overrides):
        data = {
            'date': timestamp,
            'time': at,
            'att_black': str(self.players['alice'].id),
            'def_black': str(self.players['bob'].id),
            'att_white': str(self.players['carol'].id),
            'def_white': str(self.players['dave'].id),
            'score_black': '10',
            'score_white': '8',
            'klinker_att_black': '0',
            'klinker_def_black': '0',
            'klinker_att_white': '0',
            'klinker_def_white': '0',
            'keeper_black': '0',
            'keeper_white': '0',
        }
        data.update(overrides)
        return data

    def add_match(self, score=(10, 8), day_offset=0):
        players = [self.players[name] for name in ('alice', 'bob', 'carol', 'dave')]
        match = Match(
            played_at=datetime(2025, 6, 1 + day_offset, 10),
            season=6,
            att_black=players[0].id,
            def_black=players[1].id,
            att_white=players[2].id,
            def_white=players[3].id,
        )
        db.session.add(match)
        db.session.flush()
        result = Result(
            match_id=match.id,
            created_by=players[0].id,
            status='Approved',
            score_black=score[0],
            score_white=score[1],
            klinker_att_black=1,
            klinker_def_black=2,
            klinker_att_white=3,
            klinker_def_white=4,
            keeper_black=5,
            keeper_white=6,
        )
        db.session.add(result)
        db.session.flush()
        for player in players:
            db.session.add(Rating(
                user_id=player.id, match_id=match.id, since=match.played_at,
                season=6, previous_rating=1500, rating=1520,
                previous_rating_season=1500, rating_season=1520,
            ))
        db.session.commit()
        return match

    def test_application_factory_and_public_routes(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/index').status_code, 200)
        self.assertEqual(self.client.get('/show_results').status_code, 302)
        self.assertIn('/auth/login', self.client.get('/show_results').location)
        self.assertEqual(repr(self.players['alice']), '<User alice>')
        self.assertIs(User.load_user(str(self.players['alice'].id)), self.players['alice'])

    def test_wsgi_entrypoint_exports_flask_application(self):
        from app import app as wsgi_app

        self.assertIsInstance(wsgi_app, type(self.app))

    def test_development_migration_configuration(self):
        import os

        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            app = create_app(TestConfig)
        self.assertIsNotNone(app.extensions['migrate'])

    def test_authentication_registration_and_safe_redirects(self):
        self.assertEqual(self.client.get('/auth/login').status_code, 200)
        response = self.client.post('/auth/register', data={
            'username': 'NewPlayer',
            'email': 'NEW@example.com',
            'password': 'secret',
            'password_validation': 'secret',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.query.filter_by(username='newplayer').one()
        self.assertEqual(new_user.email, 'new@example.com')
        self.assertTrue(new_user.check_password_hash('secret'))
        self.assertEqual(Rating.query.filter_by(user_id=new_user.id).one().rating, 1500)

        duplicate = self.client.post('/auth/register', data={
            'username': 'ALICE',
            'email': 'another@example.com',
            'password': 'secret',
            'password_validation': 'secret',
        })
        self.assertEqual(duplicate.status_code, 200)
        self.assertIn('Username already in use', duplicate.get_data(as_text=True))

        invalid_login = self.client.post('/auth/login', data={
            'username': 'alice', 'password': 'wrong',
        })
        self.assertEqual(invalid_login.status_code, 302)
        valid_login = self.client.post(
            '/auth/login?next=https://example.com',
            data={'username': 'ALICE', 'password': 'password'},
        )
        self.assertEqual(valid_login.location, '/index')
        self.assertEqual(self.client.get('/auth/login').location, '/index')
        self.assertEqual(self.client.get('/auth/logout').location, '/index')
        internal_redirect = self.client.post(
            '/auth/login?next=/profile',
            data={'username': 'alice', 'password': 'password'},
        )
        self.assertEqual(internal_redirect.location, '/profile')

    def test_password_reset_request_and_token_flow(self):
        self.log_in()
        self.assertEqual(self.client.get('/auth/register').location, '/index')
        self.assertEqual(self.client.get('/auth/request_password_reset').location, '/index')
        reset_token = self.players['alice'].get_reset_password_token()
        self.assertEqual(
            self.client.get(f'/auth/reset_password/{reset_token}').location,
            '/index',
        )
        self.client.get('/auth/logout')
        self.assertEqual(self.client.get('/auth/request_password_reset').status_code, 200)

        with patch('foosbam.auth.routes.send_password_reset') as send_reset:
            response = self.client.post('/auth/request_password_reset', data={
                'email': 'ALICE@example.com',
            })
            self.assertEqual(response.status_code, 302)
            send_reset.assert_called_once()
            send_reset.reset_mock()
            self.client.post('/auth/request_password_reset', data={
                'email': 'missing@example.com',
            })
            send_reset.assert_not_called()

        user = self.players['alice']
        token = user.get_reset_password_token()
        self.assertIs(User.verify_reset_password_token(token), user)
        self.assertIsNone(User.verify_reset_password_token('invalid-token'))
        self.assertEqual(self.client.get('/auth/reset_password/invalid-token').status_code, 302)
        self.assertEqual(self.client.get(f'/auth/reset_password/{token}').status_code, 200)
        response = self.client.post(f'/auth/reset_password/{token}', data={
            'password': 'new-password',
            'password_validation': 'new-password',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(user.check_password_hash('new-password'))
        self.log_in(password='new-password')
        self.assertEqual(self.client.get('/auth/reset_password/invalid-token').location, '/index')
        self.assertEqual(self.client.get('/auth/request_password_reset').location, '/index')

    def test_record_result_success_duplicate_timestamp_and_integrity_failure(self):
        self.log_in()
        self.assertEqual(self.client.get('/add_result').status_code, 200)
        response = self.client.post('/add_result', data=self.match_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Match.query.count(), 1)
        self.assertEqual(Result.query.one().status, 'Pending')
        self.assertEqual(Rating.query.filter(Rating.match_id.is_not(None)).count(), 4)

        duplicate = self.client.post('/add_result', data=self.match_data())
        self.assertEqual(duplicate.status_code, 200)
        self.assertIn('already is a game', duplicate.get_data(as_text=True))

        failed_post = self.match_data(timestamp='2025-06-02')
        with patch('foosbam.core.routes.elo.construct_dataframe', side_effect=IntegrityError('statement', {}, Exception('duplicate'))):
            failed = self.client.post('/add_result', data=failed_post)
        self.assertEqual(failed.status_code, 200)
        self.assertIn('could not be saved', failed.get_data(as_text=True))
        self.assertEqual(Match.query.count(), 1)

    def test_match_details_profile_ranking_and_season_pages(self):
        match = self.add_match()
        for day_offset in range(1, 5):
            self.add_match(day_offset=day_offset)
        self.log_in()
        self.assertEqual(self.client.get(f'/match/{match.id}').status_code, 200)
        self.assertEqual(self.client.get('/show_ranking').status_code, 200)
        self.assertEqual(self.client.get('/show_season').status_code, 302)
        self.assertIn('/show_season_ranking/', self.client.get('/show_season').location)
        self.assertEqual(self.client.get('/show_season_ranking/6').status_code, 200)
        self.assertEqual(self.client.get(f'/user/{self.players["alice"].id}').status_code, 200)
        self.assertEqual(self.client.get('/user/999').status_code, 404)

        self.assertEqual(details.get_player_name(self.players['alice'].id), 'alice')
        self.assertEqual(details.get_previous_and_current_rating(self.players['alice'].id, match.id), (1500, 1520))
        player_rows = details.get_players_from_match(match.id)
        self.assertEqual(len(player_rows), 4)
        self.assertEqual(details.enrich_player_details(player_rows, match.id)[0]['name'], 'Alice')
        match_details = details.get_match_and_result_details(match.id)
        self.assertEqual(match_details['score_black'], 10)
        self.assertIn('played_at', match_details)
        prediction = details.create_prediction_details(details.enrich_player_details(
            details.get_players_from_match(match.id), match.id
        ))
        self.assertEqual(prediction['black'], 0.5)
        self.assertEqual(prediction['white'], 0.5)

    def test_details_raise_for_unknown_records_and_match_without_result(self):
        with self.assertRaises(Exception):
            details.get_match_and_result_details(999)
        with self.assertRaises(Exception):
            details.get_players_from_match(999)
        with self.assertRaises(Exception):
            details.get_player_name(999)
        with self.assertRaises(Exception):
            details.get_previous_and_current_rating(self.players['alice'].id, 999)

        player = self.players['alice']
        match = Match(
            played_at=datetime(2025, 6, 3), season=6,
            att_black=player.id, def_black=self.players['bob'].id,
            att_white=self.players['carol'].id, def_white=self.players['dave'].id,
        )
        db.session.add(match)
        db.session.commit()
        self.assertIsNone(details.get_match_and_result_details(match.id)['score_black'])

    def test_edit_profile_case_normalization_and_duplicate_validation(self):
        self.log_in()
        self.assertEqual(self.client.get('/edit_profile').status_code, 200)
        response = self.client.post('/edit_profile', data={
            'username': 'ALICE', 'email': 'ALICE@example.com',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.players['alice'].username, 'alice')

        duplicate = self.client.post('/edit_profile', data={
            'username': 'bob', 'email': 'bob@example.com',
        })
        self.assertEqual(duplicate.status_code, 200)
        self.assertIn('already in use', duplicate.get_data(as_text=True))

    def test_form_rejects_duplicate_players_and_duplicate_email(self):
        duplicate_player_data = self.match_data(
            def_black=str(self.players['alice'].id)
        )
        registration_client = self.app.test_client()
        duplicate_email = registration_client.post('/auth/register', data={
            'username': 'another',
            'email': 'ALICE@example.com',
            'password': 'secret',
            'password_validation': 'secret',
        })
        self.assertEqual(duplicate_email.status_code, 200)
        self.assertIn('Email already in use', duplicate_email.get_data(as_text=True))

        self.log_in()
        response = self.client.post('/add_result', data=duplicate_player_data)
        self.assertEqual(response.status_code, 200, response.location)
        self.assertIn('four distinct players', response.get_data(as_text=True))

    def test_add_match_form_rejects_missing_fields_and_email_messages_render(self):
        self.log_in()
        self.assertEqual(self.client.post('/add_result', data={}).status_code, 200)

        user = self.players['alice']
        with self.app.test_request_context('/'):
            with patch('foosbam.email.send_email') as send:
                send_password_reset(user)
        send.assert_called_once()
        args, kwargs = send.call_args
        self.assertEqual(args[0], '[Foosbam] Password Reset')
        self.assertEqual(kwargs['recipients'], [user.email])
        self.assertIn('/auth/reset_password/', kwargs['text_body'])
        self.assertIn('/auth/reset_password/', kwargs['html_body'])

        with mail.record_messages() as outbox:
            send_email('subject', 'sender@example.com', ['recipient@example.com'], 'plain', '<p>html</p>')
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0].subject, 'subject')
        self.assertEqual(outbox[0].body, 'plain')
        self.assertEqual(outbox[0].html, '<p>html</p>')


if __name__ == '__main__':
    unittest.main()
