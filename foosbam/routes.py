from flask import render_template, flash, redirect, url_for
from foosbam import app
from foosbam.forms import LoginForm

@app.route('/')
@app.route('/index')
def index(): 
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        flash(f"Log in for {form.username.data}")
        return redirect(url_for('index'))
        
    return render_template('login.html', form=form)