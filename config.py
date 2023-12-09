import os
import urllib

basedir = os.path.abspath(os.path.dirname(__file__))
#params = urllib.parse.quote_plus(os.environ.get('AZURE_SQL_CONNECTION_STRING'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    #SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc:///?odbc_connect={params}"
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')