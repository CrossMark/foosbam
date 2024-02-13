from foosbam import db
from foosbam.models import Match, Result, User
import pandas as pd
from sqlalchemy.orm import aliased

def get_match_and_result_details(match_id):
    # QUERY

    # SELECT
    #   m.played_at,
    #   ab.id,
    #   ab.username,
    #   db.id
    #   db.username,
    #   aw.id,
    #   aw.username,
    #   dw.id,
    #   dw.username,
    #   r.score_black,
    #   r.score_white,
    #   r.klinker_att_black,
    #   r.klinker_att_white,
    #   r.klinker_def_black,
    #   r.klinker_def_white,
    #   r.keeper_black,
    #   r.keeper_white
    # FROM matches m
    # LEFT JOIN results r
    #   ON m.id = r.match_id
    # LEFT JOIN user ab
    #   ON m.att_black = ab.id
    # LEFT JOIN user db
    #   ON m.def_black = db.id
    # LEFT JOIN user aw
    #   ON m.att_white = aw.id
    # LEFT JOIN user dw
    #   ON m.def_white = dw.id
    # WHERE m.id = match_id


    p_ab = aliased(User)
    p_db = aliased(User)
    p_aw = aliased(User)
    p_dw = aliased(User)

    details = db.session.query(
        Match.id, 
        Match.played_at,
        Result.score_black,
        Result.score_white
    ).filter(
        Match.id == match_id
    ).join(
        Result,
        Match.id == Result.id,
        isouter = True
    )

    details_dict = dict(
            zip(
                [
                    'id',
                    'played_at',
                    'score_black',
                    'score_white'
                ],
                details[0],
            )
        )

    print(details_dict)

    # ranking = db.session.query(
    #     r1.since,
    #     User.id,
    #     User.username,
    #     r1.rating
    # ).join(
    #     r2,
    #     and_(r1.user_id == r2.user_id,
    #          r1.since < r2.since
    #     ),
    #     isouter = True
    # ).join(
    #     User,
    #     r1.user_id == User.id,
    #     isouter = True
    # ).filter(
    #     r2.user_id.is_(None)
    # ).order_by(
    #     r1.rating.desc()
    # ).order_by(
    #     r1.since
    # ).all()

    # ranking_as_dict = [
    #     dict(
    #         zip(
    #             [
    #                 'since',
    #                 'user_id',
    #                 'player',
    #                 'rating',
    #             ],
    #             rank,
    #         )
    #     )
    #     for rank in ranking
    # ]

    # df = pd.DataFrame.from_records(ranking_as_dict)

    # # Add rank column
    # df['rank'] = df['rating'].rank(method='min', ascending=False).astype(int)

    # # Change since column to Amsterdam time (for frontend) and in desired format
    # df['since'] = df['since'].apply(lambda x : routes.change_timezone(x, 'Etc/UTC', 'Europe/Amsterdam'))
    # df['since'] = df['since'].dt.strftime('%Y-%m-%d %H:%M')

    # # Use the title function on the player names, so they get capitals
    # df['player'] = df['player'].str.title()

    # return df