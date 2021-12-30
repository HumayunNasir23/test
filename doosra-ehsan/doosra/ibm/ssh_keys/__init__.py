from flask import Blueprint

ibm_ssh_keys = Blueprint('ibm_ssh_keys', __name__)

from doosra.ibm.ssh_keys import api
