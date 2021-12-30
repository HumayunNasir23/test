import os

from config import config

flask_config = os.getenv('FLASK_CONFIG') or 'default'

GENERATION = config[flask_config].GENERATION
TRANSIT_BASE_URL = "https://transit.cloud.ibm.com"
VERSION = "2020-04-03"

TRANSIT_GATEWAY_CREATE = "Task for TRANSIT_GATEWAY creation initiated by user: email '{}'"
TRANSIT_GATEWAY_CONNECTION_CREATE = "Task for TRANSIT_GATEWAY_CONNECTION creation initiated by user: email '{}'"
DELETE_TRANSIT_GATEWAY = "Task for TRANSIT_GATEWAY DELETION initiated by user: email '{}'"
DELETE_TRANSIT_GATEWAY_CONNECTION = "Task for TRANSIT_GATEWAY_CONNECTION DELETION initiated by user: email '{}'"
