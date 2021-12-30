from flask import Blueprint

gcp_instance_groups = Blueprint('gcp_instance_groups', __name__)

from doosra.gcp.instance_groups import api
