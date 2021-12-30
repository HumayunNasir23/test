from flask import Blueprint

gcp_vpc = Blueprint('gcp_vpc', __name__)

from doosra.gcp.vpc import api
