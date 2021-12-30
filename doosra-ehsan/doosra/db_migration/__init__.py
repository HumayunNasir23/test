from flask import Blueprint

db_migration = Blueprint('db_migration', __name__)

from doosra.db_migration import api
