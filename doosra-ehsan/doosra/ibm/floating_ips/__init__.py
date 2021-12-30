from flask import Blueprint

ibm_floating_ips = Blueprint('ibm_floating_ips', __name__)

from doosra.ibm.floating_ips import api
