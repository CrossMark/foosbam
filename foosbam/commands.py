from datetime import datetime, timedelta, timezone

import click
from flask import Flask, current_app
from sqlalchemy import func, select

from foosbam import db
from foosbam.core import elo, seasons
from foosbam.models import Match, Rating, Result, User

DEMO_USERNAMES = ('demo_alex', 'demo_blair', 'demo_casey', 'demo_drew', 'demo_erin')
DEMO_SEASON_COUNT = 8
DEMO_MATCHES_PER_SEASON = 15


def _add_demo_match(players, game, played_at):
    att_black, def_black, att_white, def_white, score_black, score_white = game
    match = Match(
        played_at=played_at,
        season=seasons.get_season_from_date(played_at),
        att_black=players[att_black].id,
        def_black=players[def_black].id,
        att_white=players[att_white].id,
        def_white=players[def_white].id,
    )
    db.session.add(match)
    db.session.flush()

    db.session.add(Result(
        match_id=match.id,
        created_by=players[DEMO_USERNAMES[0]].id,
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

    rating_rows = elo.construct_dataframe(
        user_ids=[
            players[att_black].id,
            players[def_black].id,
            players[att_white].id,
            players[def_white].id,
        ],
        match_id=match.id,
        played_at=played_at,
        score_black=score_black,
        score_white=score_white,
    )
    db.session.add_all(list(rating_rows['rating_obj']))


def register_cli_commands(app: Flask) -> None:
    @app.cli.command('seed-demo-data')
    def seed_demo_data() -> None:
        if not current_app.debug:
            raise click.ClickException(
                'Demo data can only be seeded with Flask debug mode enabled.'
            )
        if db.engine.dialect.name != 'sqlite':
            raise click.ClickException(
                'Demo data can only be seeded into a SQLite database.'
            )

        with db.session.begin():
            existing_demo_users = db.session.scalars(
                select(User).where(User.username.in_(DEMO_USERNAMES))
            ).all()
            if len(existing_demo_users) not in (0, len(DEMO_USERNAMES)):
                raise click.ClickException(
                    'The database contains only some demo users; no data was changed.'
                )

            if existing_demo_users:
                existing_usernames = set(
                    db.session.scalars(select(User.username)).all()
                )
                if existing_usernames != set(DEMO_USERNAMES):
                    raise click.ClickException(
                        'The database contains non-demo users; no data was changed.'
                    )

                players = {player.username: player for player in existing_demo_users}
                db.session.query(Result).delete(synchronize_session=False)
                db.session.query(Rating).delete(synchronize_session=False)
                db.session.query(Match).delete(synchronize_session=False)
                for player in existing_demo_users:
                    player.set_password(player.username)
            else:
                existing_data = any(
                    db.session.scalar(select(func.count()).select_from(model))
                    for model in (User, Match, Result, Rating)
                )
                if existing_data:
                    raise click.ClickException(
                        'The database is not empty and does not contain the complete demo dataset; '
                        'no data was changed.'
                    )

                players = {}
                for username in DEMO_USERNAMES:
                    player = User(
                        username=username,
                        email=f'{username}@example.invalid',
                    )
                    player.set_password(username)
                    db.session.add(player)
                    players[username] = player
                db.session.flush()

            initial_since = datetime(1900, 1, 1)
            db.session.add_all(
                Rating(
                    user_id=player.id,
                    match_id=None,
                    since=initial_since,
                    season=0,
                    previous_rating=None,
                    rating=1500,
                    previous_rating_season=None,
                    rating_season=1500,
                )
                for player in players.values()
            )
            db.session.flush()

            run_time = datetime.now(timezone.utc).time()
            for season in range(1, DEMO_SEASON_COUNT + 1):
                season_start, _ = seasons.get_dates_from_season(season)
                season_start_at = datetime.combine(
                    datetime.fromisoformat(season_start).date(),
                    run_time,
                    tzinfo=timezone.utc,
                )
                for game_index in range(DEMO_MATCHES_PER_SEASON):
                    rotation = (season + game_index) % len(DEMO_USERNAMES)
                    player_indexes = tuple(
                        (rotation + offset) % len(DEMO_USERNAMES)
                        for offset in range(4)
                    )
                    winner_score = 10 + 2 * (game_index % 4)
                    if game_index % 2 == 0:
                        score_black, score_white = winner_score, winner_score - 2
                    else:
                        score_black, score_white = winner_score - 2, winner_score
                    game = (
                        *(DEMO_USERNAMES[player_index] for player_index in player_indexes),
                        score_black,
                        score_white,
                    )
                    played_at = season_start_at + timedelta(days=game_index * 5)
                    _add_demo_match(players, game, played_at)

            seeded_match_count = db.session.scalar(
                select(func.count()).select_from(Match)
            )
            seeded_seasons = db.session.scalars(select(Match.season).distinct()).all()

        click.echo(
            f'Demo data refreshed with {seeded_match_count} matches across '
            f'{len(seeded_seasons)} seasons ({", ".join(map(str, sorted(seeded_seasons)))}).'
        )
        click.echo('Each demo account password is the same as its username.')
