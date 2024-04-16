from foosbam import db
from foosbam.core import misc
from foosbam.models import Rating, User
import pandas as pd
from sqlalchemy import and_
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

