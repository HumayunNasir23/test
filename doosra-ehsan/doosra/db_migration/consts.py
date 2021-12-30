import os
from config import config

flask_config = os.getenv("FLASK_CONFIG") or "default"

DB_MIGRATION_API_KEY = config[flask_config].DB_MIGRATION_API_KEY
DB_MIGRATION_URL = config[flask_config].DB_MIGRATION_CONTROLLER_HOST
REQUEST_TIMEOUT = 2  # seconds
