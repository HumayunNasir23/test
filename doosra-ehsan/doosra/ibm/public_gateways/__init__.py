from flask import Blueprint

ibm_public_gateways = Blueprint('ibm_public_gateways', __name__)

from doosra.ibm.public_gateways import api
