from flask import Blueprint

bp = Blueprint('core', __name__)

from foosbam.core import routes