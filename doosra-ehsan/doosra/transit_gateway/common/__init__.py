from flask import Blueprint

transit_common = Blueprint('transit_common', __name__)

from doosra.transit_gateway.common import api
