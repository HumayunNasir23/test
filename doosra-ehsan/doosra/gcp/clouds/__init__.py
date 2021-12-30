from flask import Blueprint

gcp_clouds = Blueprint('gcp_clouds', __name__)

from doosra.gcp.clouds import api
