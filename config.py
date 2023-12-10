import os
from urllib.parse import quote_plus

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get(quote_plus('DATABASE_URL')) or 'sqlite:///' + os.path.join(basedir, 'app.sqlite')