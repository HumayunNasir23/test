from flask import Blueprint

gcp_firewalls = Blueprint('firewalls', __name__)

from doosra.gcp.firewalls import api
