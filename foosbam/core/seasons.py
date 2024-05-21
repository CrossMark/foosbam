import datetime as dt
from dateutil.relativedelta import relativedelta
from math import ceil
from typing import Union, List
import pandas as pd

def get_season_from_date(date_arg: Union[str, pd.Timestamp]) -> int:
    """
    Determines the season number based on the provided date.

    Parameters:
    date_arg (str or pandas.Timestamp): The date for which the season number is to be determined.

    Returns:
    int: The season number corresponding to the provided date.

    Raises:
    ValueError: If the date is not in a valid format or if the provided date is before the first game date (2023-11-30).

    Example:
    >>> get_season_from_date('2023-12-15')
    1
    >>> get_season_from_date('2024-04-15')
    2
    """

    try:
        date_arg = pd.to_datetime(date_arg, utc=True)
    except ValueError:
        raise ValueError("Invalid date format. Please provide a valid date.")

    first_game_date = pd.to_datetime('2023-11-30', utc=True)
    second_season_start_date = pd.to_datetime('2024-04-01', utc=True)

    if date_arg < first_game_date:
        raise ValueError("No dates before the first game date are allowed. Please fill in a date equal to or later than 2023-11-30.")
    elif date_arg < second_season_start_date:
        return 1
    else:
        # calculate difference in quarters between date_arg and second_season_start_date
        q = (date_arg.year  * 4 + date_arg.quarter) - (second_season_start_date.year  * 4 + second_season_start_date.quarter)
        return q + 2
    
def get_dates_from_season(season: int) -> List[str]:
    """
    Calculate the start and end dates of a given season.

    Args:
        season (int): The season number. Must be a positive integer.

    Returns:
        List[str]: A list containing the start and end dates of the season in the format 'YYYY-MM-DD'.

    Raises:
        ValueError: If the season number is not a positive integer.

    Note:
        Seasons are counted starting from 1. Each season spans three months, except for season 1 which spans four months. See the example for more info.

    Examples:
        >>> get_dates_from_season(1)
        ['2023-11-30', '2024-03-30']
        >>> get_dates_from_season(2)
        ['2024-04-01', '2024-06-30']
        >>> get_dates_from_season(3)
        ['2024-07-01', '2024-09-30']
    """
    if not isinstance(season, int) or season <= 0:
        raise ValueError("Season must be a positive integer")
    
    if season == 1:  # Exception for the first season
        start_date = dt.datetime(2023, 11, 30)
        end_date = dt.datetime(2024, 3, 30)
    else:
        year = 2023 + ceil(season/4)

        if season % 4 == 0:
            quarter = 4
        else:
            quarter = season % 4

        start_month = (quarter * 3) - 2 

        start_date = dt.datetime(year, start_month, 1)
        end_date = start_date + relativedelta(months = 3) + relativedelta(days=-1)

    return [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]

def get_all_seasons() -> List[int]:
    """
    Retrieves a list of all seasons up to the current season based on the current date.

    Returns:
    list: A list containing all season numbers up to the current season.

    Example:
    >>> get_all_seasons()
    [1, 2]
    """

    today = pd.Timestamp.today('UTC')
    current_season = get_season_from_date(today)
    return list(range(1, current_season + 1))