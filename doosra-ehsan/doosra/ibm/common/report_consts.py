from doosra.common.consts import PENDING

REPORT_MESSAGE = """
{stage} for '{resource_name}' is '{status}' with message '{message}' and key '{resource_type}{path}' updated in {time}s
"""

MAIN_STEPS_PATH = "$.steps"
STAGE_STEPS_PATH = "$.steps.{stage}.steps"
RESOURCE_SUMMARY_PATH = "$.steps.{stage}.steps.{resource_type}"
RESOURCES_ARRAY_PATH = "$.steps.{stage}.steps.{resource_type}.resources"

WINDOWS_BACKUP = {
    "windows_backup": {
        "name": "Windows Backup(Instance Creation in Classic)",
        "status": PENDING,
        "message": "",
        "order": 1,
    }
}

SNAPSHOT = {
    "snapshot": {
        "name": "Snapshot (Template creation in classic)",
        "status": PENDING,
        "message": "",
        "order": 2,
    }
}
COS_EXPORT = {
    "cos_export": {
        "name": "Export image to COS",
        "status": PENDING,
        "message": "",
        "order": 3,
    }
}
QCOW2_CONVERSION = {
    "qcow2_conversion": {
        "name": "Image conversion (qcow2 conversion)",
        "status": PENDING,
        "message": "",
        "order": 4,
    }
}
CUSTOM_IMAGE_CREATION = {
    "custom_image_creation": {
        "name": "Custom image creation",
        "status": PENDING,
        "message": "",
        "order": 5,
    }
}
STATUS_KEY = "status"
ID_KEY = "id"
LINK_KEY = "link"
NAME_KEY = "name"
MESSAGE_KEY = "message"
TITLE_KEY = "title"
RESOURCES_KEY = "resources"

VPC_KEY = "vpc"
RESOURCE_GROUP_KEY = "resource_group"
SSH_KEY_KEY = "ssh_keys"
DEDICATED_HOST_KEY = "dedicated_hosts"
IKE_POLICIES_KEY = "ike_policies"
IPSEC_POLICIES_KEY = "ipsec_policies"

IPSEC_POLICIES_REPORT_TITLE = "IPSec policies"
SSH_KEY_REPORT_TITLE = "SSH keys"
DEDICATED_HOST_REPORT_TITLE = "Dedicated Hosts"
IKE_POLICIES_REPORT_TITLE = "IKE policies"

SSH_KEY_REPORT_TEMPLATE = {
    SSH_KEY_KEY: {
        TITLE_KEY: SSH_KEY_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

DEDICATED_HOST_REPORT_TEMPLATE = {
    DEDICATED_HOST_KEY: {
        TITLE_KEY: DEDICATED_HOST_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

IKE_POLICY_TEMPLATE = {
    IKE_POLICIES_KEY: {
        TITLE_KEY: IKE_POLICIES_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

IPSEC_POLICY_TEMPLATE = {
    IPSEC_POLICIES_KEY: {
        TITLE_KEY: IPSEC_POLICIES_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

ACL_REPORT_TITLE = "Access control lists"
ACL_KEY = "acls"
ACL_TEMPLATE = {
    ACL_KEY: {TITLE_KEY: ACL_REPORT_TITLE, STATUS_KEY: PENDING, RESOURCES_KEY: []}
}

SECURITY_GROUP_REPORT_TITLE = "Security groups"
SECURITY_GROUP_KEY = "security_groups"
SECURITY_GROUP_TEMPLATE = {
    SECURITY_GROUP_KEY: {
        TITLE_KEY: SECURITY_GROUP_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

PUBLIC_GATEWAY_REPORT_TITLE = "Public gateways"
PUBLIC_GATEWAY_KEY = "public_gateways"
PUBLIC_GATEWAY_TEMPLATE = {
    PUBLIC_GATEWAY_KEY: {
        TITLE_KEY: PUBLIC_GATEWAY_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

ADDRESS_PREFIX_REPORT_TITLE = "Address prefixes"
ADDRESS_PREFIX_KEY = "address_prefixes"
ADDRESS_PREFIX_TEMPLATE = {
    ADDRESS_PREFIX_KEY: {
        TITLE_KEY: ADDRESS_PREFIX_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

SUBNET_REPORT_TITLE = "Subnets"
SUBNET_KEY = "subnets"
SUBNET_TEMPLATE = {
    SUBNET_KEY: {TITLE_KEY: SUBNET_REPORT_TITLE, STATUS_KEY: PENDING, RESOURCES_KEY: []}
}

ROUTE_REPORT_TITLE = "Routes"
ROUTE_KEY = "routes"
ROUTE_TEMPLATE = {
    ROUTE_KEY: {TITLE_KEY: ROUTE_REPORT_TITLE, ROUTE_KEY: PENDING, RESOURCES_KEY: []}
}

ATTACH_PG_TO_SUBNET_REPORT_TITLE = "Attaching public gateway to subnets"
ATTACH_PG_TO_SUBNET_KEY = "attach_pg_to_subnets"
ATTACH_PG_TO_SUBNET_TEMPLATE = {
    ATTACH_PG_TO_SUBNET_KEY: {
        TITLE_KEY: ATTACH_PG_TO_SUBNET_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

INSTANCE_REPORT_TITLE = "Virtual server instances"
INSTANCE_KEY = "instances"
INSTANCE_TEMPLATE = {
    INSTANCE_KEY: {
        TITLE_KEY: INSTANCE_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

VOLUME_REPORT_TITLE = "Volumes"
VOLUME_KEY = "volumes"
VOLUME_TEMPLATE = {
    VOLUME_KEY: {TITLE_KEY: VOLUME_REPORT_TITLE, STATUS_KEY: PENDING, RESOURCES_KEY: []}
}

INSTANCE_PROFILE_REPORT_TITLE = "Instance profiles"
INSTANCE_PROFILE_KEY = "instance_profiles"
INSTANCE_PROFILE_TEMPLATE = {
    INSTANCE_PROFILE_KEY: {
        TITLE_KEY: INSTANCE_PROFILE_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

IMAGE_REPORT_TITLE = "Images"
IMAGE_KEY = "images"
IMAGE_TEMPLATE = {
    IMAGE_KEY: {TITLE_KEY: IMAGE_REPORT_TITLE, STATUS_KEY: PENDING, RESOURCES_KEY: []}
}

FLOATING_IP_REPORT_TITLE = "Floating IPs"
FLOATING_IP_KEY = "floating_ips"
FLOATING_IP_TEMPLATE = {
    FLOATING_IP_KEY: {
        TITLE_KEY: FLOATING_IP_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}
VPN_REPORT_TITLE = "VPN gateways"
VPN_KEY = "vpn_gateways"
VPN_TEMPLATE = {
    VPN_KEY: {TITLE_KEY: VPN_REPORT_TITLE, STATUS_KEY: PENDING, RESOURCES_KEY: []}
}
VPN_CONNECTION_REPORT_TITLE = "VPN connections"
VPN_CONNECTION_KEY = "vpn_connections"
VPN_CONNECTION_TEMPLATE = {
    VPN_CONNECTION_KEY: {
        TITLE_KEY: VPN_CONNECTION_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

ADDING_LOCAL_CIDR_REPORT_TITLE = "Adding local CIDRs"
ADDING_LOCAL_CIDR_KEY = "adding_local_cidrs"
ADDING_LOCAL_CIDR_TEMPLATE = {
    ADDING_LOCAL_CIDR_KEY: {
        TITLE_KEY: ADDING_LOCAL_CIDR_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

DELETING_LOCAL_CIDR_REPORT_TITLE = "Deleting local CIDRs"
DELETING_LOCAL_CIDR_KEY = "deleting_local_cidrs"
DELETING_LOCAL_CIDR_TEMPLATE = {
    DELETING_LOCAL_CIDR_KEY: {
        TITLE_KEY: DELETING_LOCAL_CIDR_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

ADDING_PEER_CIDR_REPORT_TITLE = "Adding peer CIDRs"
ADDING_PEER_CIDR_KEY = "adding_peer_cidrs"
ADDING_PEER_CIDR_TEMPLATE = {
    ADDING_PEER_CIDR_KEY: {
        TITLE_KEY: ADDING_PEER_CIDR_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

DELETING_PEER_CIDR_REPORT_TITLE = "Deleting peer CIDRs"
DELETING_PEER_CIDR_KEY = "deleting_peer_cidrs"
DELETING_PEER_CIDR_TEMPLATE = {
    DELETING_PEER_CIDR_KEY: {
        TITLE_KEY: DELETING_PEER_CIDR_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

LOAD_BALANCER_REPORT_TITLE = "Load balancers"
LOAD_BALANCER_KEY = "load_balancers"
LOAD_BALANCER_TEMPLATE = {
    LOAD_BALANCER_KEY: {
        TITLE_KEY: LOAD_BALANCER_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

KUBERNETES_REPORT_TITLE = "IKS Clusters"
KUBERNETES_KEY = "iks_clusters"
KUBERNETES_CLUSTER_REPORT_TEMPLATE = {
    KUBERNETES_KEY: {
        TITLE_KEY: KUBERNETES_REPORT_TITLE,
        STATUS_KEY: PENDING,
        RESOURCES_KEY: [],
    }
}

CLUSTER_BACKUP = {
    "backup": {
        "name": "Taking workloads Backup",
        "status": PENDING,
        "message": "",
        "order": 1,
    }
}

CLUSTER_PROVISIONING = {
    "provisioning": {
        "name": "Provisioning IKS Cluster",
        "status": PENDING,
        "message": "",
        "order": 2,
    }
}

CLUSTER_RESTORE = {
    "restore": {
        "name": "Restoring Workloads",
        "status": PENDING,
        "message": "",
        "order": 3,
    }
}
