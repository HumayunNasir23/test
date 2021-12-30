from flask import Blueprint

transit_gateway = Blueprint('transit_gateways', __name__)

from doosra.transit_gateway import api
