from flask import Blueprint

migration = Blueprint('migrate', __name__)

from doosra.migration import api
