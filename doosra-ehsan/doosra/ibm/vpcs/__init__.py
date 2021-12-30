from flask import Blueprint

ibm_vpcs = Blueprint('ibm_vpcs', __name__)

from doosra.ibm.vpcs import api
