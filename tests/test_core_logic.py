import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd

from foosbam import create_app, db
from foosbam.core import elo, misc, ranking, rating, seasons
from foosbam.models import Match, Rating, Result, User


class TestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True


class DatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def add_player(self, username):
        player = User(username=username, email=f'{username}@example.com')
        player.set_password('password')
        db.session.add(player)
        db.session.flush()
        return player

    def add_match(self, players, played_at=None, season=3, score=(10, 8)):
        played_at = played_at or datetime(2024, 7, 1)
        match = Match(
            played_at=played_at,
            season=season,
            att_black=players[0].id,
            def_black=players[1].id,
            att_white=players[2].id,
            def_white=players[3].id,
        )
        db.session.add(match)
        db.session.flush()
        db.session.add(Result(
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
        ))
        return match


class SeasonAndTimezoneTests(unittest.TestCase):
    def test_season_boundaries_and_dates(self):
        self.assertEqual(seasons.get_season_from_date('2023-11-30'), 1)
        self.assertEqual(seasons.get_season_from_date('2024-03-31'), 1)
        self.assertEqual(seasons.get_season_from_date('2024-04-01'), 2)
        self.assertEqual(seasons.get_season_from_date('2024-07-01'), 3)
        self.assertEqual(seasons.get_season_from_date('2025-01-01'), 5)
        self.assertEqual(seasons.get_dates_from_season(1), ['2023-11-30', '2024-03-31'])
        self.assertEqual(seasons.get_dates_from_season(4), ['2024-10-01', '2024-12-31'])
        self.assertEqual(seasons.get_dates_from_season(5), ['2025-01-01', '2025-03-31'])

    def test_season_invalid_values_and_current_season_list(self):
        with self.assertRaisesRegex(ValueError, 'Invalid date format'):
            seasons.get_season_from_date('not-a-date')
        with self.assertRaisesRegex(ValueError, 'No dates before'):
            seasons.get_season_from_date('2023-11-29')
        for value in (0, -1, 1.5, '1'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'positive integer'):
                seasons.get_dates_from_season(value)

        with patch.object(seasons.pd.Timestamp, 'today', return_value=pd.Timestamp('2024-08-01', tz='UTC')):
            self.assertEqual(seasons.get_all_seasons(), [1, 2, 3])

    def test_timezone_conversion(self):
        converted = misc.change_timezone(
            datetime(2024, 1, 1, 12), 'Etc/UTC', 'Europe/Amsterdam'
        )
        self.assertEqual(converted, datetime(2024, 1, 1, 13, tzinfo=converted.tzinfo))
        self.assertEqual(converted.tzinfo.key, 'Europe/Amsterdam')


class EloTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.players = [self.add_player(name) for name in ('alice', 'bob', 'carol', 'dave')]
        db.session.flush()
        for player in self.players:
            db.session.add(Rating(
                user_id=player.id, match_id=None, since=datetime(1900, 1, 1),
                season=0, previous_rating=None, rating=1500,
                previous_rating_season=None, rating_season=1500,
            ))
        db.session.commit()

    def test_rating_lookup_match_counts_and_season_default(self):
        first_match = self.add_match(
            self.players, datetime(2024, 7, 1), season=3
        )
        db.session.add(Rating(
            user_id=self.players[0].id, match_id=first_match.id,
            since=first_match.played_at, season=3, previous_rating=1500,
            rating=1570, previous_rating_season=1500, rating_season=1570,
        ))
        later_match = self.add_match(
            self.players, datetime(2024, 7, 2), season=3
        )
        db.session.add(Rating(
            user_id=self.players[0].id, match_id=later_match.id,
            since=later_match.played_at, season=3, previous_rating=1570,
            rating=1600, previous_rating_season=1570, rating_season=1600,
        ))
        db.session.commit()

        self.assertEqual(elo.get_most_recent_rating(self.players[0].id), 1600)
        self.assertEqual(elo.get_most_recent_rating(self.players[0].id, 3), 1600)
        self.assertEqual(elo.get_most_recent_rating(self.players[0].id, 4), 1500)
        self.assertEqual(elo.get_current_match_count(self.players[0].id), 2)
        self.assertEqual(
            elo.get_match_count_before(self.players[0].id, datetime(2024, 7, 2)), 1
        )

    def test_rating_lookup_propagates_unexpected_database_errors(self):
        with patch.object(elo.db.session, 'scalar', side_effect=RuntimeError('database error')):
            with self.assertRaisesRegex(RuntimeError, 'database error'):
                elo.get_most_recent_rating(self.players[0].id, 3)

    def test_rating_formula_helpers_and_dataframe(self):
        self.assertAlmostEqual(elo.calculate_expected_score(1500, 1500), 0.5)
        self.assertGreater(elo.calculate_expected_score(1600, 1500), 0.5)
        self.assertEqual(elo.get_winner(10, 8), 'black')
        self.assertEqual(elo.get_winner(8, 10), 'white')
        self.assertGreater(elo.calculate_point_factor(10, 8), 2)
        self.assertEqual(elo.calculate_k_factor({'num_games': 0}), 50)
        self.assertEqual(elo.calculate_k_factor({'num_games': 300}), 25)

        match = self.add_match(self.players, datetime(2024, 7, 1), season=3)
        df = elo.construct_dataframe(
            [player.id for player in self.players],
            match.id, match.played_at, 10, 8,
        )
        self.assertEqual(df['team'].tolist(), ['black', 'black', 'white', 'white'])
        self.assertEqual(len(df['rating_obj']), 4)
        self.assertTrue(all(item.rating > 0 for item in df['rating_obj']))
        self.assertTrue(all(item.rating_season > 0 for item in df['rating_obj']))
        self.assertEqual(elo.get_opponent_ratings(df, df.iloc[0], False), [1500, 1500])
        self.assertEqual(elo.get_opponent_ratings(df, df.iloc[0], True), [1500, 1500])

    def test_player_team_expectations_and_new_rating_season_paths(self):
        frame = pd.DataFrame({
            'team': ['black', 'black', 'white', 'white'],
            'rating': [1600, 1400, 1500, 1500],
            'rating_season': [1600, 1400, 1500, 1500],
            'opp_ratings': [[1500, 1500]] * 4,
            'opp_ratings_season': [[1500, 1500]] * 4,
            'num_games': [10, 20, 30, 40],
        })
        frame['k_factor'] = frame.apply(elo.calculate_k_factor, axis=1)
        frame['player_expected'] = frame.apply(
            lambda row: elo.calculate_expected_player_score(row, False), axis=1
        )
        frame = elo.calculate_expected_team_score(frame, False)
        frame['player_expected_season'] = frame.apply(
            lambda row: elo.calculate_expected_player_score(row, True), axis=1
        )
        frame = elo.calculate_expected_team_score(frame, True)
        black = frame.iloc[0]
        white = frame.iloc[2]
        self.assertAlmostEqual(black['team_expected'], white['team_expected'])
        self.assertGreater(
            elo.calculate_new_rating(black, 2, 'black', False), black['rating']
        )
        self.assertLess(
            elo.calculate_new_rating(white, 2, 'black', False), white['rating']
        )
        self.assertGreater(
            elo.calculate_new_rating(black, 2, 'black', True), black['rating_season']
        )
        self.assertLess(
            elo.calculate_new_rating(white, 2, 'black', True), white['rating_season']
        )
        self.assertEqual(elo.calculate_rating(frame, 8, 10)['new_rating'].shape, (4,))


class RatingAndRankingTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.players = [self.add_player(name) for name in ('alice', 'bob', 'carol', 'dave')]

    def test_initial_and_historical_ratings_are_created_idempotently(self):
        rating.add_initial_ratings(db)
        rating.add_initial_ratings(db)
        self.assertEqual(Rating.query.filter_by(match_id=None).count(), 4)

        players = self.players
        for index in range(5):
            match = self.add_match(
                players, datetime(2024, 7, 1) + timedelta(days=index), season=3
            )
        rating.create_existing_ratings(db)
        self.assertEqual(Rating.query.filter(Rating.match_id.is_not(None)).count(), 20)
        self.assertEqual(Rating.query.count(), 24)

    def test_fill_database_creates_initial_ratings_without_matches(self):
        rating.fill_database(db)
        self.assertEqual(Rating.query.count(), len(self.players))
        self.assertEqual(Match.query.count(), 0)

    def test_rankings_include_qualified_players_and_handle_empty_season(self):
        rating.add_initial_ratings(db)
        for index in range(5):
            match = self.add_match(
                self.players, datetime(2024, 7, 1) + timedelta(days=index), season=3
            )
            for offset, player in enumerate(self.players):
                db.session.add(Rating(
                    user_id=player.id, match_id=match.id, since=match.played_at,
                    season=3, previous_rating=1500, rating=1600 - offset * 50,
                    previous_rating_season=1500, rating_season=1600 - offset * 50,
                ))
        db.session.commit()

        current = ranking.get_current_ranking()
        seasonal = ranking.get_season_ranking(3)
        self.assertEqual(current['rank'].tolist(), [1, 2, 3, 4])
        self.assertEqual(current.iloc[0]['player'], 'Alice')
        self.assertEqual(seasonal.iloc[0]['rating'], 1600)
        self.assertEqual(seasonal.iloc[0]['rank'], 1)
        self.assertTrue(ranking.get_season_ranking(99).empty)
