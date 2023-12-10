from datetime import datetime
from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required
from foosbam import db
from foosbam.models import Match, Result, User
from foosbam.core import bp
from foosbam.core.forms import AddMatchForm

@bp.route('/')
@bp.route('/index')
def index(): 
    return render_template("index.html")

@bp.route('/add_result', methods=['GET', 'POST'])
@login_required
def add_result():
    form = AddMatchForm()
    players = [(p.id, p.username) for p in User.query.order_by('username')]
    form.att_black.choices = form.def_black.choices = form.att_white.choices = form.def_white.choices = players

    if request.method == 'GET':
        form.date.data = datetime.now().date()
        form.time.data = datetime.now().time()
        form.klinker_att_black.data = 0
        form.klinker_def_black.data = 0
        form.klinker_att_white.data = 0
        form.klinker_def_white.data = 0
        form.keeper_black.data = 0
        form.keeper_white.data = 0

    if form.validate_on_submit():
        played_at_timestamp = datetime.combine(form.date.data, form.time.data)

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
    results = Result.query.join(Match).add_columns(
        Match.played_at,
        Match.att_black,
        Match.def_black,
        Match.att_white,
        Match.def_white,
        Result.score_black,
        Result.score_white,
        Result.status
    ).all()
    print(type(results[0][1]))
    return render_template("core/show_results.html", results=results)