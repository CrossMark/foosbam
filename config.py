import os
from urllib.parse import quote_plus

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get(quote_plus('DATABASE_URL')) or 'sqlite:///' + os.path.join(basedir, 'app.sqlite')
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_recycle' : 280}

    MAIL_SERVER = os.environ.get('MAIL_SERVER') 
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')