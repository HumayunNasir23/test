from flask import Blueprint

gcp_load_balancers = Blueprint('gcp_load_balancers', __name__)

from doosra.gcp.load_balancers import api
