from config import Config
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

login = LoginManager()
login.login_view = 'auth.login'
login.login_message_category = "is-danger"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    if os.environ.get('FLASK_ENV') == 'development':
        migrate.init_app(app, db, render_as_batch=True)
    else:
        migrate.init_app(app, db)
    mail.init_app(app)
    login.init_app(app)

    from foosbam.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from foosbam.core import bp as core_bp
    app.register_blueprint(core_bp)

    return app

from foosbam import models