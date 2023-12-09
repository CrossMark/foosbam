from flask import render_template, flash, redirect, url_for, request
from foosbam import app, db
from foosbam.forms import LoginForm, RegistrationForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from foosbam.models import User
from urllib.parse import urlsplit

@app.route('/')
@app.route('/index')
@login_required
def index(): 
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    # redirect already logged in users to home page
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        # try to get User from database
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data)
        )

        # if user is not found or password is not correct, redirect to login page
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        
        # else login user
        login_user(user, remember=form.remember_me.data)

        # extract next_page
        next_page = request.args.get('next')

        # if next_page is not found, redirect to index. else to next_page
        if not next_page or urlsplit(next_page).netloc != '':
            next_age = url_for('index')
        return redirect(next_page)
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # redirect already logged in users to home page
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash(f"Have fun with Foosbam, {user.username}!")

        return redirect(url_for('login'))
    return render_template('register.html', form=form)