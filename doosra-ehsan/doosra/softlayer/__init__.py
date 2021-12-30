from flask import Blueprint

softlayer = Blueprint('softlayer', __name__)

from doosra.softlayer import api
