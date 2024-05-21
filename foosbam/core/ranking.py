from foosbam import db
from foosbam.core import misc
from foosbam.models import Rating, User
import pandas as pd
from sqlalchemy import and_, func
from sqlalchemy.orm import aliased

def get_current_ranking():
    r1 = aliased(Rating)
    r2 = aliased(Rating)

    ranking = db.session.query(
        r1.since,
        User.id,
        User.username,
        r1.rating
    ).join(
        r2,
        and_(r1.user_id == r2.user_id,
             r1.since < r2.since
        ),
        isouter = True
    ).join(
        User,
        r1.user_id == User.id,
        isouter = True
    ).filter(
        r2.user_id.is_(None)
    ).order_by(
        r1.rating.desc()
    ).order_by(
        r1.since
    ).all()

    ranking_as_dict = [
        dict(
            zip(
                [
                    'since',
                    'user_id',
                    'player',
                    'rating',
                ],
                rank,
            )
        )
        for rank in ranking
    ]

    df = pd.DataFrame.from_records(ranking_as_dict)

    # Add rank column
    df['rank'] = df['rating'].rank(method='min', ascending=False).astype(int)

    # Change since column to Amsterdam time (for frontend) and in desired format
    df['since'] = df['since'].apply(lambda x : misc.change_timezone(x, 'Etc/UTC', 'Europe/Amsterdam'))
    df['since'] = df['since'].dt.strftime('%Y-%m-%d %H:%M')

    # Use the title function on the player names, so they get capitals
    df['player'] = df['player'].str.title()

    return df

def get_season_ranking(season):
    r1 = aliased(Rating)

    # In this subquery we first get the latest rating for the given season for each user.
    # Furthermore we count the number of matches for a user in the given season.
    latest_season_rating_subquery = db.session.query(
        r1.user_id,
        func.count(r1.match_id).label('match_count'),
        func.max(r1.since).label('max_since')
    ).filter(
        r1.season == season
    ).group_by(
        r1.user_id
    ).subquery()

    # Join the actual rating and the User table to the subquery
    ranking = db.session.query(
        r1.since,
        User.id,
        User.username,
        r1.rating_season,
    ).join(
        latest_season_rating_subquery,
        and_(r1.user_id == latest_season_rating_subquery.c.user_id,
             r1.since == latest_season_rating_subquery.c.max_since,
             latest_season_rating_subquery.c.match_count >= 5           # only include ratings for players with a match count of 5 and higher
            ),
    ).join(
        User,
        r1.user_id == User.id,
    ).order_by(
        r1.rating_season.desc()
    ).order_by(
        r1.since
    ).all()

    ranking_as_dict = [
        dict(
            zip(
                [
                    'since',
                    'user_id',
                    'player',
                    'rating',
                ],
                rank,
            )
        )
        for rank in ranking
    ]

    df = pd.DataFrame.from_records(ranking_as_dict)

    if len(df) > 0:
        # Add rank column
        df['rank'] = df['rating'].rank(method='min', ascending=False).astype(int)

        # Change since column to Amsterdam time (for frontend) and in desired format
        df['since'] = df['since'].apply(lambda x : misc.change_timezone(x, 'Etc/UTC', 'Europe/Amsterdam'))
        df['since'] = df['since'].dt.strftime('%Y-%m-%d %H:%M')

        # Use the title function on the player names, so they get capitals
        df['player'] = df['player'].str.title()

    return df

