from flask import Blueprint

ibm_instances = Blueprint('ibm_instances', __name__)

from doosra.ibm.instances import api
