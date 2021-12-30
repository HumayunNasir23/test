from flask import Blueprint

ibm_templates = Blueprint('ibm_templates', __name__)

from doosra.vpc_templates import api
