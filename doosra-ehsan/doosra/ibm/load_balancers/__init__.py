from flask import Blueprint

ibm_load_balancers = Blueprint('ibm_load_balancers', __name__)

from doosra.ibm.load_balancers import api
