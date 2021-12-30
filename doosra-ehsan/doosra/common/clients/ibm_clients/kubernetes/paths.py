LIST_CLASSIC_KUBERNETES_CLUSTERS_PATH = "classic/getClusters"
GET_CLASSIC_KUBERNETES_CLUSTERS_WORKER_POOLS_PATH = "/clusters/{cluster}/workerpools"
GET_CLASSIC_KUBERNETES_CLUSTERS_SUBNET_PATH = "/clusters/{cluster}/subnets"
GET_CLASSIC_KUBERNETES_CLUSTER_KUBE_CONFIG_PATH = "getKubeconfig?cluster={cluster}&format=json&admin=true"

CREATE_VPC_KUBERNETES_CLUSTER_PATH = [
    "POST", "{{kubernetes_base_url}}/v2/vpc/createCluster"]
CREATE_VPC_KUBERNETES_WORKERPOOL_PATH = "vpc/createWorkerPool"
GET_VPC_KUBERNETES_CLUSTER_DETAIL_PATH = [
    "GET", "{{kubernetes_base_url}}/v2/vpc/getCluster?cluster={cluster}&showResources=true"]
GET_VPC_KUBERNETES_CLUSTER_KUBE_CONFIG_PATH = [
    "GET", "{{kubernetes_base_url}}/v2/getKubeconfig?cluster={cluster}&format=json&admin=true"]

# IBM Kubernetes Manages View Paths
LIST_K8S_CLUSTERS_PATH = "vpc/getClusters?provider={provider}"
LIST_ALL_K8S_CLUSTER_PATH = "vpc/getClusters"
LIST_ZONE_FLAVORS_FOR_CLUSTER_CREATION = "getFlavors?zone={zone}&provider={provider}"
LIST_ALL_LOCATIONS = "locations"
GET_K8S_KUBE_VERSIONS = "getVersions"
GET_K8S_CLUSTERS_DETAIL_PATH = "vpc/getCluster?cluster={cluster}&showResources=true"
GET_K8S_CLUSTERS_WORKER_POOL_PATH = "vpc/getWorkerPools?cluster={cluster}"
GET_K8S_CLUSTER_KUBE_CONFIG = "getKubeconfig?cluster={cluster}&format=json&admin=true"
