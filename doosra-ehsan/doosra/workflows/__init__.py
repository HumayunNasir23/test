from flask import Blueprint

ibm_workflows = Blueprint('workflows', __name__)

from doosra.workflows import api
