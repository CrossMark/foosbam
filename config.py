import os
import urllib

params = urllib.parse.quote_plus(os.environ.get('AZURE_SQL_CONNECTION_STRING'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc:///?odbc_connect={params}"