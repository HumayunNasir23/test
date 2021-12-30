from flask import Blueprint

users = Blueprint('users', __name__)

from doosra.users import api
