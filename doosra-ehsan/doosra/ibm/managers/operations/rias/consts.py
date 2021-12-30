import os
from config import config
from doosra.common.clients.ibm_clients.consts import VPC_DATE_BASED_VERSION

flask_config = os.getenv('FLASK_CONFIG') or 'default'

# Default region for IBM
DEFAULT_REGION = "us-south"

# RIAS URL consts
GENERATION = config[flask_config].GENERATION
RIAS_BASE_URL = "https://{region}.iaas.cloud.ibm.com"
KUBERNETES_CLUSTER_BASE_URL = "https://containers.cloud.ibm.com/global"
VERSION = VPC_DATE_BASED_VERSION

# Status consts
AVAILABLE = "available"
ATTACHED = "attached"
ACTIVE = "active"
FAILED = "failed"
RUNNING = "running"
STABLE = "stable"
PENDING = "pending"
DEPRECATED = "deprecated"
CREATE_PENDING = "create_pending"
DELETE_PENDING = "delete_pending"
DELETING = "deleting"
MAINTENANCE_PENDING = "maintenance_pending"
UPDATE_PENDING = "update_pending"
PAUSED = "paused"
PAUSING = "pausing"
RESTARTING = "restarting"
RESUMING = "resuming"
STOPPING = "stopping"
STARTING = "starting"
STOPPED = "stopped"
NORMAL = "normal"
DEPLOYING = "deploying"
WARNING = "warning"
CLUSTER_DELETED = "deleted"
UPDATING = "updating"
CRITICAL = "critical"
REQUESTED = "requested"
