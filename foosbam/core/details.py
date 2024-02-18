from datetime import datetime
from foosbam import db
from foosbam.core import routes
from foosbam.models import Match, Result, Rating, User
from typing import Dict, Union

def get_match_and_result_details(match_id: int) -> Dict[str, Union[int, str]]:
    """
    Retrieves details of a specific match and its result from the database.

    Args:
        match_id (int): The ID of the match to retrieve details for.

    Returns:
        dict: A dictionary containing details of the match and its result, with the following keys:
            - 'id' (int): The ID of the match.
            - 'played_at' (str): The date and time the match was played, in 'YYYY-MM-DD HH:MM' format, 
                                 converted from UTC to Europe/Amsterdam timezone.
            - 'score_black' (int): The score of the black team.
            - 'score_white' (int): The score of the white team.
            - 'klinker_att_black' (int): The number of klinkers scored by the black attacker.
            - 'klinker_def_white' (int): The number of klinkers scored by the black defender.
            - 'klinker_att_white' (int): The number of klinkers scored by the white attacker.
            - 'klinker_def_white' (int): The number of klinkers scored by the white defender.
            - 'keeper_black' (str): The number of keeper goals scored by the black team.
            - 'keeper_white' (str): The number of keeper goals scored by the white team.

    Raises:
        Exception: If there's an error while querying the database.
    """

    try:
        details = db.session.query(
            Match.id, 
            Match.played_at,
            Result.score_black,
            Result.score_white,
            Result.klinker_att_black,
            Result.klinker_def_black,
            Result.klinker_att_white,
            Result.klinker_def_white,
            Result.keeper_black,
            Result.keeper_white
        ).filter(
            Match.id == match_id
        ).join(
            Result,
            Match.id == Result.id,
            isouter = True
        ).one()

        match_details = dict(
            zip(
                [
                    'id',
                    'played_at',
                    'score_black',
                    'score_white',
                    'klinker_att_black',
                    'klinker_def_black',
                    'klinker_att_white',
                    'klinker_def_white',
                    'keeper_black',
                    'keeper_white'
                ],
                details,
            )
        )
        
        match_details['played_at'] = routes.change_timezone(match_details['played_at'], 'Etc/UTC', 'Europe/Amsterdam')
        match_details['played_at'] = datetime.strftime(match_details['played_at'], '%Y-%m-%d %H:%M')
        
        return match_details
    except Exception as e:
        raise e

def get_previous_and_current_rating(user_id : int, match_id : int):
    """
    """
    try:
        details = db.session.query(
            Rating.previous_rating,
            Rating.rating
        ).filter(
            Rating.user_id == user_id,
            Rating.match_id == match_id
        ).one()
        return details
    except Exception as e:
        raise e

def get_players_from_match(match_id: int):
    try:
        player_ids = db.session.query(
            Match.att_black,
            Match.def_black,
            Match.att_white,
            Match.def_white
        ).filter(
            Match.id == match_id
        ).one()

        att_black = {'id': player_ids[0]}
        def_black = {'id': player_ids[1]}
        att_white = {'id': player_ids[2]}
        def_white = {'id': player_ids[3]}


        return [att_black, def_black, att_white, def_white]
    
    except Exception as e:
        raise e

def get_player_name(user_id : int) ->  str:
    """
    """
    try:
        name = db.session.query(
            User.username,
        ).filter(
            User.id == user_id,
        ).one()

        return name[0]  # name is a tuple with 1 element, so only return the actual name
    except Exception as e:
        raise e
    
