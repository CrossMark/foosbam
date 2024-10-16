from datetime import datetime
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from foosbam import db
from foosbam.models import Match, Result, User
from foosbam.core import bp, details, elo, misc, ranking, seasons
from foosbam.core.forms import AddMatchForm, EditProfileForm
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import aliased
from zoneinfo import ZoneInfo

@bp.route('/')
@bp.route('/index')
def index(): 
    return render_template("index.html")

@bp.route('/add_result', methods=['GET', 'POST'])
@login_required
def add_result():
    form = AddMatchForm()
    players = [(p.id, p.username.title()) for p in User.query.order_by('username')]
    form.att_black.choices = form.def_black.choices = form.att_white.choices = form.def_white.choices = players

    # Set default values for form
    if request.method == 'GET':
        form.date.data = datetime.now(ZoneInfo('Europe/Amsterdam')).date()
        form.time.data = datetime.now(ZoneInfo('Europe/Amsterdam')).time()
        form.klinker_att_black.data = 0
        form.klinker_def_black.data = 0
        form.klinker_att_white.data = 0
        form.klinker_def_white.data = 0
        form.keeper_black.data = 0
        form.keeper_white.data = 0

    if form.validate_on_submit():
        played_at_timestamp = misc.change_timezone(datetime.combine(form.date.data, form.time.data), 'Europe/Amsterdam', 'Etc/UTC')

        # Add match to database
        match = Match(
            played_at=played_at_timestamp,
            season=seasons.get_season_from_date(played_at_timestamp), 
            att_black=form.att_black.data, 
            def_black=form.def_black.data, 
            att_white=form.att_white.data, 
            def_white=form.def_white.data
        )
        db.session.add(match)
        db.session.flush()

        # Add result to database
        result = Result(
            match_id = match.id,
            created_by = current_user.id,
            status = "Pending",
            score_black = form.score_black.data,
            score_white = form.score_white.data,
            klinker_att_black = form.klinker_att_black.data,
            klinker_att_white = form.klinker_att_white.data,
            klinker_def_black = form.klinker_def_black.data,
            klinker_def_white = form.klinker_def_white.data,
            keeper_black = form.keeper_black.data,
            keeper_white = form.keeper_white.data
        )
        db.session.add(result)
        db.session.flush()

        # Calculate new ratings and add them to database

        ## Prepare arguments
        user_ids = [
            form.att_black.data,
            form.def_black.data,
            form.att_white.data,
            form.def_white.data
        ]     
        
        df = elo.construct_dataframe(
            user_ids = user_ids, 
            match_id = match.id, 
            played_at = match.played_at, 
            score_black = result.score_black, 
            score_white = result.score_white, 
        )
            

        ## Add new ratings to database
        db.session.add_all(list(df['rating_obj']))
        db.session.commit()
        return redirect(url_for('core.index'))

    return render_template("core/add_result.html", form=form)

@bp.route('/show_results')
@login_required
def show_results():

    u_att_black = aliased(User)
    u_def_black = aliased(User)
    u_att_white = aliased(User)
    u_def_white = aliased(User)

    results = db.session.query(
        Match.id,
        Match.played_at,
        u_att_black.username.label('att_black'),              
        u_def_black.username.label('def_black'),                
        u_att_white.username.label('att_white'),              
        u_def_white.username.label('def_white'),                
        Result.score_black,     
        Result.score_white,       
        Result.status
    ).join(
        Match,
        Result.match_id == Match.id
    ).join(
        u_att_black,
        Match.att_black == u_att_black.id
    ).join(
        u_def_black,
        Match.def_black == u_def_black.id
    ).join(
        u_att_white,
        Match.att_white == u_att_white.id
    ).join(
        u_def_white,
        Match.def_white == u_def_white.id
    ).all()

    results_as_dict = [
        dict(
            zip(
                [
                    'id',
                    'played_at',
                    'att_black',
                    'def_black',
                    'att_white',
                    'def_white',
                    'score_black',
                    'score_white',
                    'status',
                ],
                result,
            )
        )
        for result in results
    ]

    df = pd.DataFrame.from_records(results_as_dict)

    if len(df) > 0:
        df = df.sort_values(by='played_at', ascending=False)

        # Change played_at column to Amsterdam time (for frontend) and in desired format
        df['played_at'] = df['played_at'].apply(lambda x : misc.change_timezone(x, 'Etc/UTC', 'Europe/Amsterdam'))
        df['played_at'] = df['played_at'].dt.strftime('%Y-%m-%d %H:%M')

        # Use the title function on the player names, so they get capitals
        for col in ['att_black', 'def_black', 'att_white', 'def_white']:
            df[col] = df[col].str.title()
    
    return render_template("core/show_results.html", results=df)

@bp.route('/match/<match_id>')
@login_required
def match(match_id):
    # Get match results
    match_details = details.get_match_and_result_details(match_id)

    # Get players
    player_details = details.get_players_from_match(match_id)

    # For each player, get name and ratings before and after match
    player_details = details.enrich_player_details(player_details, match_id)

    # Get prediction details
    prediction_details = details.create_prediction_details(player_details)

    return render_template("core/match.html", 
                           match_details=match_details, 
                           att_black=player_details[0],
                           def_black=player_details[1],
                           att_white=player_details[2],
                           def_white=player_details[3],
                           prediction_details=prediction_details
                        )

@bp.route('/show_ranking')
@login_required
def show_ranking():
    r = ranking.get_current_ranking()
    return render_template("core/show_ranking.html", ranking=r)

@bp.route('/show_season')
@login_required
def show_season():
    season = seasons.get_season_from_date(datetime.today())
    return redirect(url_for('core.show_season_ranking', season=season))

@bp.route('/show_season_ranking/<season>')
@login_required
def show_season_ranking(season):
    season = int(season)
    r = ranking.get_season_ranking(season)
    season_dates = seasons.get_dates_from_season(season)
    return render_template("core/show_season_ranking.html", season=season, season_dates=season_dates, ranking=r)

@bp.route('/user/<user_id>')
@login_required
def user(user_id):
    user = db.first_or_404(sa.select(User).where(User.id == user_id))

    u_att_black = aliased(User)
    u_def_black = aliased(User)
    u_att_white = aliased(User)
    u_def_white = aliased(User)

    results = db.session.query(
        Match.id,
        Match.played_at,
        u_att_black.username.label('att_black'),              
        u_def_black.username.label('def_black'),                
        u_att_white.username.label('att_white'),              
        u_def_white.username.label('def_white'),                
        Result.score_black,     
        Result.score_white,       
        Result.status
    ).join(
        Match,
        Result.match_id == Match.id
    ).join(
        u_att_black,
        Match.att_black == u_att_black.id
    ).join(
        u_def_black,
        Match.def_black == u_def_black.id
    ).join(
        u_att_white,
        Match.att_white == u_att_white.id
    ).join(
        u_def_white,
        Match.def_white == u_def_white.id
    ).filter(
        (Match.def_white == user_id) | (Match.att_white == user_id) | (Match.def_black == user_id) | (Match.att_black == user_id)
    ).all()

    results_as_dict = [
        dict(
            zip(
                [
                    'id',
                    'played_at',
                    'att_black',
                    'def_black',
                    'att_white',
                    'def_white',
                    'score_black',
                    'score_white',
                    'status',
                ],
                result,
            )
        )
        for result in results
    ]

    df = pd.DataFrame.from_records(results_as_dict)

    if len(df) > 0:
        df = df.sort_values(by='played_at', ascending=False)

        # Change played_at column to Amsterdam time (for frontend) and in desired format
        df['played_at'] = df['played_at'].apply(lambda x : misc.change_timezone(x, 'Etc/UTC', 'Europe/Amsterdam'))
        df['played_at'] = df['played_at'].dt.strftime('%Y-%m-%d %H:%M')

        # Use the title function on the player names, so they get capitals
        for col in ['att_black', 'def_black', 'att_white', 'def_white']:
            df[col] = df[col].str.title()
    
    return render_template("core/user.html", user=user, results=df)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()

    if request.method == 'GET':
        form.username.data = current_user.username.title()
        form.email.data = current_user.email

    if form.validate_on_submit():
        current_user.username = form.username.data.lower()
        current_user.email = form.email.data.lower()
        db.session.commit()
        flash('Your changes have been saved.', 'is-success')
        return redirect(url_for('core.user', user_id = current_user.id))
    
    return render_template('core/edit_profile.html', form=form)