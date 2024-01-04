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

from foosbam.models import Match, Rating, Result, User
import math

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

    ## get already played matches (in order!)
    matches = [(m.id, m.att_black, m.def_black, m.att_white, m.def_white) for m in Match.query.order_by('played_at')]

    ## get results of already played matches
    results = [(r.match_id, r.score_black, r.score_white) for r in Result.query]

    


def fill_database(db):
    add_initial_ratings(db)
    create_existing_ratings(db)