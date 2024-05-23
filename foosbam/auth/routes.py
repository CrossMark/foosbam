from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from foosbam import db
from foosbam.auth import bp
from foosbam.auth.forms import LoginForm, RegistrationForm, ResetPasswordForm, RequestPasswordResetForm
from foosbam.core import seasons
from foosbam.email import send_password_reset
from foosbam.models import User, Rating
import sqlalchemy as sa
from urllib.parse import urlsplit
from datetime import datetime

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # redirect already logged in users to home page
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))

    form = LoginForm()
    if form.validate_on_submit():
        # try to get User from database
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data.lower())
        )

        # if user is not found or password is not correct, redirect to login page
        if user is None or not user.check_password_hash(form.password.data):
            flash('Invalid username or password', 'is-danger')
            return redirect(url_for('auth.login'))
        
        # else login user
        login_user(user, remember=form.remember_me.data)

        # extract next_page
        next_page = request.args.get('next')

        # if next_page is not found, redirect to index. else to next_page
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('core.index')
        return redirect(next_page)
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('core.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    # redirect already logged in users to home page
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))
    
    form = RegistrationForm()

    if form.validate_on_submit():
        # add new user to users table
        user = User(username=form.username.data.lower(), email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # add initial rating for new user to ratings table
        rating = Rating(user_id=user.id, rating=1500, season=seasons.get_season_from_date(datetime.today()), rating_season=1500)
        db.session.add(rating)
        db.session.commit()

        flash(f"Have fun with Foosbam, {user.username.title()}!", "is-success")

        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@bp.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    # redirect already logged in users to home page
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))

    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        # try to get User from database
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data.lower())
        )

        # if user is found, send email
        if user:
            send_password_reset(user)

        flash('Check your email for password reset instructions!', 'is-info')
        return redirect(url_for('auth.login')) 
    return render_template('auth/request_password_reset.html', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # redirect already logged in users to home page
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))
    
    user = User.verify_reset_password_token(token)

    if not user:
        return redirect(url_for('core.index'))
    
    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.', 'is-success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

