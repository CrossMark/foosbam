from flask import Blueprint

bp = Blueprint('auth', __name__)

from foosbam.auth import routes