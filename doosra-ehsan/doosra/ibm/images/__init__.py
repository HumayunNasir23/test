from flask import Blueprint

ibm_images = Blueprint('ibm_images', __name__)

from doosra.ibm.images import api
