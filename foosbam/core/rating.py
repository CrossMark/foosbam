from datetime import datetime
from foosbam.core import elo, seasons
from foosbam.models import Match, Rating, Result, User 


def add_initial_ratings(db):
    # add inital rating for every user,
    # but only IF rating does not exist yet for this user

    # get current players
    players = [p.id for p in User.query]

    ## get players that already have a rating
    players_with_rating = [p.user_id for p in db.session.query(Rating.user_id).distinct()]

    # get players without rating
    players_without_rating = [p for p in players if p not in players_with_rating]

    # create initial ratings for every player
    since_date = datetime.strptime('1900-01-01', '%Y-%m-%d')
    ratings = [Rating(user_id=pid, rating=1500, since=since_date, season=0, rating_season=1500) for pid in players_without_rating]

    # add initial ratings to database
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
        df = elo.construct_dataframe(players, match.id, match.played_at, match.score_black, match.score_white)

        db.session.add_all(list(df['rating_obj']))

    db.session.commit()


def fill_database(db):
    add_initial_ratings(db)
    create_existing_ratings(db)