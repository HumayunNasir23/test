from .consts import RESOURCE_MANAGER_MAJOR_VERSION, VPC_MAJOR_VERSION

AUTH_URL = "https://iam.cloud.ibm.com/identity/token"

VPC_BASE_URL = "https://{region}.iaas.cloud.ibm.com"
VPC_URL_TEMPLATE = ''.join([VPC_BASE_URL, "/", VPC_MAJOR_VERSION, "/", "{path}"])

RESOURCE_MANAGER_BASE_URL = "https://resource-controller.cloud.ibm.com"
RESOURCE_MANAGER_URL_TEMPLATE = ''.join([RESOURCE_MANAGER_BASE_URL, "/", RESOURCE_MANAGER_MAJOR_VERSION, "/", "{path}"])

KUBERNETES_CLUSTER_BASE_URL = "https://containers.cloud.ibm.com/global"
KUBERNETES_CLUSTER_URL_TEMPLATE = ''.join([KUBERNETES_CLUSTER_BASE_URL, "/", RESOURCE_MANAGER_MAJOR_VERSION, "/",
                                           "{path}"])
CLASSIC_KUBERNETES_CLUSTERS_URL_TEMPLATE = ''.join([KUBERNETES_CLUSTER_BASE_URL, "/", VPC_MAJOR_VERSION, "/",
                                                    "{path}"])
