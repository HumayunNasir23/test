from flask import Blueprint

ibm_security_groups = Blueprint('ibm_security_groups', __name__)

from doosra.ibm.security_groups import api
