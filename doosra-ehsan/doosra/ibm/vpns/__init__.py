from flask import Blueprint

ibm_vpns = Blueprint('ibm_vpns', __name__)

from doosra.ibm.vpns import api
