from flask import Blueprint

ibm_k8s = Blueprint('ibm_k8s', __name__)

from doosra.ibm.kubernetes import api
