# Steps we need:

# HAPPY FLOW
# -----------
# Game gets added to matches and results. The submit button on the Add Game page also triggers calculating ELO scores.
# For every player, calculate new elo
# For the two attackers, calculate new att elo
# For the two defenders, calculate new def elo
#
#
# ELO CALCULATION
# ---------------
# 1) Get latest rating from table (for each player)
# 2) Calculate expected score against opponents (for each player)
# 3) Calculate expected score for team (for each team)
# 4) Calculate point factor (once)
# 5) Calculate K factor (for each player)
# 6) Calculate new ELO rating (for each player)
# 7) Add rating to table

#
# DO NOT FORGET
# -------------
# When a new player registers, add a record for this player in the 3 ratings tables, with the default rating.
# Functionality for recalculating ELO scores over all (accepted) games

from foosbam import db
from foosbam.models import Match, Rating, Result, User
import math
import pandas as pd
import sqlalchemy as sa


def get_most_recent_rating(user_id):
    # QUERY
    ## SELECT * FROM ratings 
    ## WHERE user_id = form.att_black.data 
    ## ORDER BY since DESC 
    ## LIMIT 1

    query = sa.select(Rating).where(Rating.user_id == user_id).order_by(Rating.since.desc())
    rating = db.session.scalar(query).rating
    return rating

def get_current_match_count(user_id):
    # QUERY
    ## SELECT COUNT(match_id) FROM matches
    ## WHERE user_id IN (att_black, def_black, att_white, def_white)
    count = Match.query.filter((Match.att_black == user_id) | (Match.def_black == user_id) | (Match.att_white == user_id) | (Match.def_white == user_id)).count()
    return count

def get_match_count_before(user_id, before_timestamp):
    # QUERY
    ## SELECT COUNT(match_id) FROM matches
    ## WHERE user_id IN (att_black, def_black, att_white, def_white)
    ## AND played_at < before_timestamp

    count = Match.query.filter((Match.att_black == user_id) | (Match.def_black == user_id) | (Match.att_white == user_id) | (Match.def_white == user_id)). \
         filter(Match.played_at < before_timestamp). \
         count()
    return count

def construct_dataframe(user_ids, match_id, played_at, score_black, score_white):
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

    ratings = [get_most_recent_rating(user_id) for user_id in user_ids]

    counts = [get_match_count_before(user_id, played_at) for user_id in user_ids]

    df = pd.DataFrame(list(zip(user_ids, roles, teams, ratings, counts)), columns=["user_id", "role", "team", "rating", "num_games"])

    # CALCULATE NEW RATINGS
    df_new_rating = calculate_rating(df, score_black, score_white)
    df['rating_obj'] = df_new_rating.apply(lambda x : Rating(user_id=x['user_id'], match_id=match_id, rating=x['new_rating']), axis=1)

    return df

def get_opponent_ratings(df, row):
    own_team = row['team']
    opp_ratings = df[df['team'] != own_team]['rating'].tolist()
    return opp_ratings

def calculate_expected_score(rating_player, rating_opponent):
    prob_player = 1 / (1 + 10 ** ((rating_opponent - rating_player) / 400))
    return prob_player

def calculate_expected_player_score(row):
    own_rating = row['rating']
    exp_score = 0
    for opp_rating in row['opp_ratings']:
        exp_score = exp_score + calculate_expected_score(own_rating, opp_rating)
    exp_score = exp_score / 2
    return exp_score

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

def calculate_new_rating(row, point_factor, winner):
    if row['team'] == winner:
        return int(round(row['rating'] + row['k_factor'] * point_factor  * (1 - row['player_expected']), 0))
    else:
        return int(round(row['rating'] + row['k_factor'] * point_factor  * (0 - row['player_expected']), 0))
    
def calculate_rating(df, score_black, score_white):
    df['opp_ratings'] = df.apply(lambda x : get_opponent_ratings(df, x), axis=1)
    df['player_expected'] = df.apply(lambda x : calculate_expected_player_score(x), axis=1)
    df['k_factor'] = df.apply(lambda x : calculate_k_factor(x), axis=1)
    point_factor = calculate_point_factor(score_black, score_white)
    winner = get_winner(score_black, score_white)
    df['new_rating'] = df.apply(lambda x : calculate_new_rating(x, point_factor, winner), axis=1)
    return df

def add_initial_ratings(db):
    # add inital rating for every user

    ## get current players
    players = [p.id for p in User.query]

    ## create initial ratings for every player
    ratings = [Rating(user_id=pid, rating=1500) for pid in players]

    ## add initial ratings to database
    db.session.add_all(ratings)
    db.session.commit()

def create_existing_ratings(db):
    # loop over all matches already played and add ratings for these matches

    ## get already played matches and results (in order!)

    matches = db.session.query(
        Match.id,
        Match.played_at,
        Match.att_black,              
        Match.def_black,                
        Match.att_white,              
        Match.def_white,                
        Result.score_black,     
        Result.score_white,       
    ).join(
        Match,
        Result.match_id == Match.id
    ).order_by('played_at')

    for match in matches:
        players = [match.att_black, match.def_black, match.att_white, match.def_white]
        df = construct_dataframe(players, match.id, match.played_at, match.score_black, match.score_white)

        db.session.add_all(list(df['rating_obj']))

    db.session.commit()


def fill_database(db):
    add_initial_ratings(db)
    create_existing_ratings(db)