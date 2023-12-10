from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

if os.environ.get('FLASK_ENV') == 'development':
    migrate = Migrate(app, db, render_as_batch=True)
else:
    migrate = Migrate(app, db)

login = LoginManager(app)
login.login_view = 'login'

from foosbam import routes, models