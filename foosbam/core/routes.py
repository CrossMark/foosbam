from datetime import datetime
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from foosbam import db
from foosbam.models import Match, Result, User
from foosbam.core import bp, details, elo, misc, ranking, seasons
from foosbam.core.forms import AddMatchForm, EditProfileForm
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
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

        try:
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
        except IntegrityError:
            db.session.rollback()
            flash('This result could not be saved because it already exists.', 'is-danger')
            return render_template("core/add_result.html", form=form)

        return redirect(url_for('core.index'))

    return render_template("core/add_result.html", form=form)

@bp.route('/show_results')
@login_required
def show_results():
    return _render_result_table('core/show_results.html')


def _render_result_table(template, user=None):
    user_aliases = {
        'att_black': aliased(User),
        'def_black': aliased(User),
        'att_white': aliased(User),
        'def_white': aliased(User),
    }
    query = db.session.query(
        Match.id.label('id'),
        Match.played_at.label('played_at'),
        Match.season.label('season'),
        *(alias.username.label(name) for name, alias in user_aliases.items()),
        Result.score_black.label('score_black'),
        Result.score_white.label('score_white'),
        Result.status.label('status'),
    ).join(Result, Result.match_id == Match.id)

    for name, alias in user_aliases.items():
        query = query.join(alias, getattr(Match, name) == alias.id)

    if user is not None:
        query = query.filter(
            sa.or_(
                Match.att_black == user.id,
                Match.def_black == user.id,
                Match.att_white == user.id,
                Match.def_white == user.id,
            )
        )

    search = request.args.get('q', '').strip()[:100]
    if search:
        query = query.filter(sa.or_(
            *(alias.username.ilike(f'%{search}%') for alias in user_aliases.values())
        ))

    seasons_available = [
        row[0] for row in db.session.query(Match.season).distinct().order_by(Match.season.desc())
    ]
    selected_season = request.args.get('season', type=int)
    if selected_season in seasons_available:
        query = query.filter(Match.season == selected_season)
    else:
        selected_season = None

    kruipen_filter = request.args.get('kruipen', 'all')
    if kruipen_filter == 'only':
        query = query.filter(sa.or_(
            Result.score_black <= 0,
            Result.score_white <= 0,
        ))
    else:
        kruipen_filter = 'all'

    sort_columns = {
        'date': Match.played_at,
        **{name: alias.username for name, alias in user_aliases.items()},
        'score_black': Result.score_black,
        'score_white': Result.score_white,
    }
    sort = request.args.get('sort', 'date')
    if sort not in sort_columns:
        sort = 'date'
    direction = request.args.get('direction', 'desc')
    if direction not in ('asc', 'desc'):
        direction = 'desc'
    sort_column = sort_columns[sort]
    ordering = sort_column.asc() if direction == 'asc' else sort_column.desc()
    query = query.order_by(ordering, Match.id.desc())

    page = max(request.args.get('page', 1, type=int) or 1, 1)
    per_page = request.args.get('per_page', 25, type=int) or 25
    per_page = min(max(per_page, 1), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    results = []
    for result in pagination.items:
        row = dict(result._mapping)
        row['is_kruipen'] = row['score_black'] <= 0 or row['score_white'] <= 0
        row['played_at'] = misc.change_timezone(
            row['played_at'], 'Etc/UTC', 'Europe/Amsterdam'
        ).strftime('%Y-%m-%d %H:%M')
        for name in user_aliases:
            row[name] = row[name].title()
        results.append(row)

    return render_template(
        template,
        user=user,
        results=results,
        pagination=pagination,
        seasons=seasons_available,
        selected_season=selected_season,
        search=search,
        sort=sort,
        direction=direction,
        per_page=per_page,
        kruipen_filter=kruipen_filter,
    )

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
    return _render_result_table('core/user.html', user=user)

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