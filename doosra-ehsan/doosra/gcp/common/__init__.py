from flask import Blueprint

gcp = Blueprint('gcp', __name__)

from doosra.gcp.common import api
