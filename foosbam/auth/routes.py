from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from foosbam import db
from foosbam.auth import bp
from foosbam.auth.forms import LoginForm, RegistrationForm
from foosbam.models import User, Rating, Rating_att, Rating_def
import sqlalchemy as sa
from urllib.parse import urlsplit

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
        rating = Rating(user_id=user.id, rating=1500)
        rating_att = Rating_att(user_id=user.id, rating=1500)
        rating_def = Rating_def(user_id=user.id, rating=1500)
        db.session.add(rating)
        db.session.add(rating_att)
        db.session.add(rating_def)
        db.session.commit()

        flash(f"Have fun with Foosbam, {user.username.title()}!", "is-success")

        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)