import unittest
from unittest.mock import patch

from foosbam import create_app, db
from foosbam.models import Match, Rating, Result, User


class TestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    DEBUG = True


class DemoDataCommandTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.runner = self.app.test_cli_runner()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_seed_refreshes_games_and_preserves_page_size_coverage(self):
        first_run = self.runner.invoke(args=['seed-demo-data'])

        self.assertEqual(first_run.exit_code, 0, first_run.output)
        self.assertIn('password is the same as its username', first_run.output)
        self.assertEqual(User.query.count(), 5)
        self.assertEqual(Match.query.count(), 120)
        self.assertEqual(Result.query.count(), 120)
        self.assertEqual(Rating.query.count(), 485)
        original_match_times = {match.played_at for match in Match.query.all()}
        self.assertTrue(User.query.filter_by(username='demo_alex').one().check_password_hash('demo_alex'))
        seeded_seasons = {
            season for (season,) in db.session.query(Match.season).distinct()
        }
        self.assertGreater(len(seeded_seasons), 2)
        self.assertTrue(any(season > 2 for season in seeded_seasons))
        self.assertIn(1, seeded_seasons)
        self.assertIn(2, seeded_seasons)
        for result in Result.query.all():
            self.assertGreaterEqual(abs(result.score_black - result.score_white), 2)
            self.assertGreaterEqual(max(result.score_black, result.score_white), 10)
        self.assertTrue(any(
            abs(result.score_black - result.score_white) > 2
            for result in Result.query.all()
        ))

        client = self.app.test_client()
        demo_alex = User.query.filter_by(username='demo_alex').one()
        with client.session_transaction() as session:
            session['_user_id'] = str(demo_alex.id)
            session['_fresh'] = True
        first_page = client.get('/show_results?per_page=100')
        self.assertEqual(first_page.status_code, 200)
        self.assertIn('Page 1 of 2 (120 matches)', first_page.get_data(as_text=True))

        demo_alex.set_password('changed-password')
        db.session.commit()
        db.session.remove()
        second_run = self.runner.invoke(args=['seed-demo-data'])

        self.assertEqual(second_run.exit_code, 0, second_run.output)
        self.assertIn('refreshed with 120 matches across', second_run.output)
        self.assertEqual(User.query.count(), 5)
        self.assertEqual(Match.query.count(), 120)
        self.assertEqual(Result.query.count(), 120)
        self.assertEqual(Rating.query.count(), 485)
        self.assertTrue(original_match_times.isdisjoint(
            match.played_at for match in Match.query.all()
        ))
        self.assertTrue(User.query.filter_by(username='demo_alex').one().check_password_hash('demo_alex'))

    def test_seed_requires_debug_mode(self):
        self.app.config['DEBUG'] = False

        result = self.runner.invoke(args=['seed-demo-data'])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('debug mode enabled', result.output)
        self.assertEqual(User.query.count(), 0)

    def test_seed_rejects_unsupported_database_and_unmanaged_data(self):
        self.app.config['DEBUG'] = True
        with patch.object(db.engine.dialect, 'name', 'postgresql'):
            unsupported = self.runner.invoke(args=['seed-demo-data'])
        self.assertNotEqual(unsupported.exit_code, 0)
        self.assertIn('SQLite database', unsupported.output)

        db.session.add(User(
            username='demo_alex',
            email='demo_alex@example.invalid',
            password_hash='unused',
        ))
        db.session.commit()
        partial = self.runner.invoke(args=['seed-demo-data'])
        self.assertNotEqual(partial.exit_code, 0)
        self.assertIn('only some demo users', partial.output)
        self.assertEqual(User.query.count(), 1)

        db.session.remove()
        db.drop_all()
        db.create_all()
        db.session.add(User(
            username='regular',
            email='regular@example.com',
            password_hash='unused',
        ))
        db.session.commit()
        unmanaged = self.runner.invoke(args=['seed-demo-data'])
        self.assertNotEqual(unmanaged.exit_code, 0)
        self.assertIn('not empty', unmanaged.output)

    def test_seed_rejects_non_demo_user_alongside_complete_demo_accounts(self):
        self.app.config['DEBUG'] = True
        result = self.runner.invoke(args=['seed-demo-data'])
        self.assertEqual(result.exit_code, 0, result.output)
        db.session.add(User(
            username='regular',
            email='regular@example.com',
            password_hash='unused',
        ))
        db.session.commit()

        mixed = self.runner.invoke(args=['seed-demo-data'])

        self.assertNotEqual(mixed.exit_code, 0)
        self.assertIn('non-demo users', mixed.output)


if __name__ == '__main__':
    unittest.main()
