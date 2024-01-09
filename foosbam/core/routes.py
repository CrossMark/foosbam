from datetime import datetime
from zoneinfo import ZoneInfo
from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required
from foosbam import db
from foosbam.models import Match, Result, User
from foosbam.core import bp
from foosbam.core.forms import AddMatchForm
import pandas as pd
from sqlalchemy.orm import aliased

def change_timezone(from_dt, from_timezone, to_timezone):
    from_dt = from_dt.replace(tzinfo=ZoneInfo(from_timezone))
    to_dt = from_dt.astimezone(ZoneInfo(to_timezone))
    return to_dt

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
        played_at_timestamp = change_timezone(datetime.combine(form.date.data, form.time.data), 'Europe/Amsterdam', 'Etc/UTC')

        match = Match(
            played_at=played_at_timestamp, 
            att_black=form.att_black.data, 
            def_black=form.def_black.data, 
            att_white=form.att_white.data, 
            def_white=form.def_white.data
        )

        db.session.add(match)
        db.session.flush()

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
    df = df.sort_values(by='played_at', ascending=False)

    # Change played_at column to Amsterdam time (for frontend) and in desired format
    df['played_at'] = df['played_at'].apply(lambda x : change_timezone(x, 'Etc/UTC', 'Europe/Amsterdam'))
    df['played_at'] = df['played_at'].dt.strftime('%Y-%m-%d %H:%M')

    # Use the title function on the player names, so they get capitals
    for col in ['att_black', 'def_black', 'att_white', 'def_white']:
        df[col] = df[col].str.title()
    
    return render_template("core/show_results.html", results=df)