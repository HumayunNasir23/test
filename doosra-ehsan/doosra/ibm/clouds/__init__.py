from flask import Blueprint

ibm_clouds = Blueprint('ibm_clouds', __name__)

from doosra.ibm.clouds import api
