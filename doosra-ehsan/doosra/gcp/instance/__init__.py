from flask import Blueprint

gcp_instance = Blueprint('instance', __name__)

from doosra.gcp.instance import api
