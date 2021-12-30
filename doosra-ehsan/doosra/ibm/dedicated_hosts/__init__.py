from flask import Blueprint

ibm_dedicated_hosts = Blueprint('ibm_dedicated_hosts', __name__)

from doosra.ibm.dedicated_hosts import api
