# ELO CALCULATION
# ---------------
# 1) Get latest rating from table (for each player)
# 2) Calculate expected score against opponents (for each player)
# 3) Calculate expected score for team (for each team)
# 4) Calculate point factor (once)
# 5) Calculate K factor (for each player)
# 6) Calculate new ELO rating (for each player)
# 7) Add rating to table

from datetime import datetime
from foosbam import db
from foosbam.core import seasons
from foosbam.models import Match, Rating
import math
import pandas as pd
import sqlalchemy as sa
from typing import Optional

def get_most_recent_rating(user_id: int, season: Optional[int] = None) -> int:
    """
    Retrieve the most recent rating for a given user. 
    If a season is specified, retrieve the most recent rating for that season. If no rating for that season exists, set it to the default rating (1500).

    Args:
        user_id (int): The ID of the user.
        season (Optional[int]): The season to filter ratings by. If None, fetch the most recent rating regardless of season.

    Returns:
        int: The most recent rating.
    """
    if season is None: # season=None returns most recent rating
        query = sa.select(Rating).where(Rating.user_id == user_id).order_by(Rating.since.desc())
        rating = db.session.scalar(query).rating
    else:
        query = sa.select(Rating).where(Rating.user_id == user_id).where(Rating.season == season).order_by(Rating.since.desc())

        try:
            rating = db.session.scalar(query).rating_season
        except AttributeError:
            # It can happen that the season parameter is filled in, but there are no ratings for that season. 
            # This means this user has not played any games yet in this season and we need the default rating.
            rating = 1500
        except Exception as e:
            raise

    return rating

def get_current_match_count(user_id: int) -> int:
    """
    Retrieve the current (total) match count for a given user. The match count is independent of seasons.

    Args:
        user_id (int): The ID of the user whose matches are being counted.

    Returns:
        int: The count of matches in which the user is involved.
    """
    count = Match.query.filter(
        (Match.att_black == user_id) | 
        (Match.def_black == user_id) | 
        (Match.att_white == user_id) | 
        (Match.def_white == user_id)
    ).count()
    return count

def get_match_count_before(user_id: int, before_timestamp: datetime) -> int:
    """
    Retrieve the match count for a given user, that were played before a given timestamp. The match count is independent of seasons.

    Args:
        user_id (int): The ID of the user whose matches are being counted.
        before_timestamp (datetime): The timestamp before which the matches were played. 

    Returns:
        int: The number of matches involving the user before the specified timestamp.
    """
    count = Match.query.filter(
        (Match.att_black == user_id) | 
        (Match.def_black == user_id) | 
        (Match.att_white == user_id) | 
        (Match.def_white == user_id)
    ).filter(
        Match.played_at < before_timestamp
    ).count()
    return count

def construct_dataframe(user_ids, match_id, played_at, score_black, score_white):
    # Prepare arguments
    roles = [
        'att_black',
        'def_black',
        'att_white',
        'def_white'
    ]
    teams = [
        'black',
        'black',
        'white',
        'white'
    ]
    season = seasons.get_season_from_date(played_at)
    ratings = [get_most_recent_rating(user_id, None) for user_id in user_ids]
    ratings_season = [get_most_recent_rating(user_id, season) for user_id in user_ids]
    counts = [get_match_count_before(user_id, played_at) for user_id in user_ids]

    df = pd.DataFrame(list(zip(user_ids, roles, teams, ratings, ratings_season, counts)), columns=["user_id", "role", "team", "rating", "rating_season", "num_games"])

    # CALCULATE NEW RATINGS
    df_new_rating = calculate_rating(df, score_black, score_white)
    df['rating_obj'] = df_new_rating.apply(
        lambda x : Rating(
            user_id = x['user_id'], 
            match_id = match_id, 
            since = played_at,
            season = season,
            previous_rating = x['rating'], 
            rating = x['new_rating'],
            previous_rating_season = x['rating_season'],
            rating_season = x['new_rating_season']
        ), 
        axis=1
    )

    return df

def get_opponent_ratings(df, row, season):
    own_team = row['team']
    if season:
        opp_ratings = df[df['team'] != own_team]['rating_season'].tolist()
    else:
        opp_ratings = df[df['team'] != own_team]['rating'].tolist()
    return opp_ratings

def calculate_expected_score(rating_player, rating_opponent):
    prob_player = 1 / (1 + 10 ** ((rating_opponent - rating_player) / 400))
    return prob_player

def calculate_expected_player_score(row, season):
    if season:
        own_rating = row['rating_season']
        exp_score = 0
        for opp_rating in row['opp_ratings_season']:
            exp_score = exp_score + calculate_expected_score(own_rating, opp_rating)
        exp_score = exp_score / 2
    else:
        own_rating = row['rating']
        exp_score = 0
        for opp_rating in row['opp_ratings']:
            exp_score = exp_score + calculate_expected_score(own_rating, opp_rating)
        exp_score = exp_score / 2
    return exp_score

def calculate_expected_team_score(df, season):
    '''Calculate average value per team and add it as a new column to the input dataframe'''
    if season:
        df['team_expected_season'] = df.groupby('team')['player_expected_season'].transform('mean')
    else:
        df['team_expected'] = df.groupby('team')['player_expected'].transform('mean')
    return df


def calculate_k_factor(row):
    return 50 / (1 + row['num_games'] / 300)

def calculate_point_factor(score_black, score_white):
    score_difference = abs(score_black - score_white)
    return 2 + (math.log(score_difference + 1) / math.log(10)) ** 3

def get_winner(score_black, score_white):
    if score_black > score_white:
        return "black"
    else:
        return "white"

def calculate_new_rating(row, point_factor, winner, season):
    if season:
        if row['team'] == winner:
            return int(round(row['rating_season'] + row['k_factor'] * point_factor  * (1 - row['team_expected_season']), 0))
        else:
            return int(round(row['rating_season'] + row['k_factor'] * point_factor  * (0 - row['team_expected_season']), 0))        
    else:
        if row['team'] == winner:
            return int(round(row['rating'] + row['k_factor'] * point_factor  * (1 - row['team_expected']), 0))
        else:
            return int(round(row['rating'] + row['k_factor'] * point_factor  * (0 - row['team_expected']), 0))
    
def calculate_rating(df, score_black, score_white):
    point_factor = calculate_point_factor(score_black, score_white)
    winner = get_winner(score_black, score_white)
    df['k_factor'] = df.apply(lambda x : calculate_k_factor(x), axis=1)

    df['opp_ratings'] = df.apply(lambda x : get_opponent_ratings(df, x, False), axis=1)
    df['player_expected'] = df.apply(lambda x : calculate_expected_player_score(x, False), axis=1)
    df = calculate_expected_team_score(df, False)
    df['new_rating'] = df.apply(lambda x : calculate_new_rating(x, point_factor, winner, False), axis=1)

    df['opp_ratings_season'] = df.apply(lambda x : get_opponent_ratings(df, x, True), axis=1)
    df['player_expected_season'] = df.apply(lambda x : calculate_expected_player_score(x, True), axis=1)
    df = calculate_expected_team_score(df, True)
    df['new_rating_season'] = df.apply(lambda x : calculate_new_rating(x, point_factor, winner, True), axis=1)
    return df