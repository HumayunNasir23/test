import json
import logging

from flask import Response, request, jsonify

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.clients.ibm_clients import K8sClient
from doosra.common.consts import *
from doosra.ibm.kubernetes.schemas import *
from doosra.ibm.kubernetes import ibm_k8s
from doosra.ibm.kubernetes.consts import *
from doosra.common.clients.ibm_clients.kubernetes.utils import K8s
from doosra.validate_json import validate_json
from doosra.models import (
    IBMCloud,
    IBMTask,
    IBMVpcNetwork,
    IBMSubnet,
    KubernetesCluster,
    KubernetesClusterWorkerPool,
    KubernetesClusterWorkerPoolZone,

)

LOGGER = logging.getLogger(__name__)


@ibm_k8s.route('/k8s/k8s_clusters/<cluster_id>/workloads', methods=['GET'])
@authenticate
def get_k8s_cluster_workloads(user_id, user, cluster_id):
    """
    Get latest Workloads of a cluster
    :param user: object of the user initiating the request
    :param user_id: ID of the user initiating the request
    :return: Response object from flask package
    """
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(project_id=user.project.id)
            .first()
    )
    if not cloud:
        LOGGER.info(
            "No IBM cloud found with ID {id}".format(id=cloud.id)
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not cloud.service_credentials:
        return Response("ERROR_COS_CREDENTIALS_MISSING", status=400)

    k8s_cluster = (
        doosradb.session.query(KubernetesCluster)
            .filter_by(id=cluster_id, cloud_id=cloud.id)
            .first()
    )
    if not k8s_cluster:
        return Response(f"ERROR_CLUSTER_NOT_FOUND_{cluster_id}", status=404)

    if k8s_cluster.status != CREATED:
        return Response("ERROR_UNSTABLE_CLUSTER_STATE", status=403)

    k8s_client = K8sClient(cloud.id)
    kube_config = k8s_client.get_k8s_cluster_kube_config(cluster=k8s_cluster.resource_id)
    kube_config = K8s(configuration_json=kube_config)
    k8s_workloads = []
    namespaces = kube_config.client.CoreV1Api().list_namespace(watch=False)
    for namespace in namespaces.items:
        temp = {"namespace": "", "pod": [], "svc": [], "pvc": []}
        if namespace.metadata.name != "velero":
            temp["namespace"] = namespace.metadata.name
            pods = kube_config.client.CoreV1Api().list_namespaced_pod(namespace=namespace.metadata.name)
            if pods.items:
                for pod in pods.items:
                    temp["pod"].append(pod.metadata.name)
            pvcs = kube_config.client.CoreV1Api().list_namespaced_persistent_volume_claim(
                namespace=namespace.metadata.name)
            if pvcs.items:
                for pvc in pvcs.items:
                    temp["pvc"].append(
                        {"name": pvc.metadata.name, "size": pvc.spec.resources.requests['storage']})
            svcs = kube_config.client.CoreV1Api().list_namespaced_service(namespace=namespace.metadata.name)
            if svcs.items:
                for svc in svcs.items:
                    temp["svc"].append(svc.metadata.name)
            k8s_workloads.append(temp)
    return Response(json.dumps(k8s_workloads), mimetype='application/json', status=200)


@ibm_k8s.route('/k8s/k8s_clusters', methods=['GET'])
@authenticate
def list_k8s_clusters(user_id, user):
    """
    List Kubernetes Cluster
    :param user: object of the user initiating the request
    :param user_id: ID of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = (
        doosradb.session.query(IBMCloud)
            .filter_by(project_id=user.project.id)
            .all()
    )
    if not ibm_cloud_accounts:
        LOGGER.info(
            "No IBM Cloud accounts found for project with ID {}".format(user.project.id)
        )
        return Response(status=404)

    k8s_clusters_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue
        k8s_clusters = ibm_cloud.kubernetes_clusters.all()
        for k8s_cluster in k8s_clusters:
            cluster = k8s_cluster.to_json()
            cluster["region"] = k8s_cluster.ibm_vpc_network.region

            if cluster["workloads"]:
                if type(k8s_cluster.workloads) == str:
                    cluster["workloads"] = json.loads(k8s_cluster.workloads)
                else:
                    cluster["workloads"] = json.loads(json.dumps(k8s_cluster.workloads))
            else:
                cluster["workloads"] = []

            k8s_clusters_list.append(cluster)

    if not k8s_clusters_list:
        return Response(status=204)


    return Response(json.dumps(k8s_clusters_list), mimetype='application/json', status=200)


@ibm_k8s.route('/k8s/k8s_clusters/worker_pools', methods=['POST'])
@validate_json(ibm_add_kubernetes_cluster_workerpool_schema)
@authenticate
def create_ibm_k8s_workerpool(user_id, user):
    """
    Create Workerpool of Kubernetes Cluster
    :param user: object of the user initiating the request
    :param user_id: ID of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.kubernetes_tasks import task_create_ibm_k8s_workerpool
    data = request.get_json(force=True)
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(project_id=user.project.id)
            .first()
    )
    if not cloud:
        LOGGER.info(
            "No IBM cloud found with ID {id}".format(id=data["cloud_id"])
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not cloud.service_credentials:
        return Response("ERROR_COS_CREDENTIALS_MISSING", status=400)

    cluster = (
        doosradb.session.query(KubernetesCluster)
            .filter_by(id=data["cluster_id"], cloud_id=cloud.id)
            .first()
    )

    if not cluster:
        return Response(f"ERROR_CLUSTER_NOT_FOUND_{data['cluster_id']}", status=404)

    if cluster.status != CREATED:
        return Response("ERROR_UNSTABLE_CLUSTER_STATE", status=403)

    worker_pool = (
        doosradb.session.query(KubernetesClusterWorkerPool)
            .filter_by(name=data['name'], kubernetes_cluster_id=cluster.id)
            .first()
    )

    if worker_pool:
        LOGGER.info("Workerpool with name of {} already exist in the cluster {}".format(worker_pool.name, cluster.name))
        return Response("ERROR_WORKER_POOL_NAME_CONFLICT", status=409)

    vpc = (
        doosradb.session.query(IBMVpcNetwork)
            .filter_by(id=cluster.ibm_vpc_network.id, cloud_id=cloud.id)
            .first()
    )

    if not vpc:
        LOGGER.info("No IBM VPC found with ID {id}".format(id=cluster.ibm_vpc_network.id))
        return Response("ERROR_VPC_NOT_FOUND",status=404)

    subnets = (
        doosradb.session.query(IBMSubnet)
            .filter_by(vpc_id=vpc.id)
            .all()
    )

    if not subnets:
        LOGGER.info("No IBM SUBNETS found within VPC ID {id}".format(id=data['vpc_id']))
        return Response(status=404)

    ibm_subnet_names = list()

    for subnet in subnets:
        ibm_subnet_names.append(subnet.name)

    for zone in data['zones']:
        if not zone['subnet'] in ibm_subnet_names:
            return Response("ERROR_SUBNET_NOT_FOUND_WITH_NAME: {}".format(zone['subnet']), status=404)

    k8s_workerpool = KubernetesClusterWorkerPool(
        name=data['name'],
        flavor=data['flavor'],
        worker_count=data['worker_count'],
        disk_encryption=data.get('disk_encryption') or True
    )
    k8s_workerpool.kubernetes_clusters = cluster

    for zone in data['zones']:
        k8s_workerpool_zone = KubernetesClusterWorkerPoolZone(
            name = zone['name']
        )
        for subnet in subnets:
            if subnet.name == zone['subnet']:
                k8s_workerpool_zone.subnets.append(subnet)
        k8s_workerpool.zones.append(k8s_workerpool_zone)
    doosradb.session.add(k8s_workerpool)

    # Create Task for Creation of Cluster
    task = IBMTask(
        region=vpc.region,
        task_id=None,
        action="ADD",
        cloud_id=cloud.id,
        resource_id=k8s_workerpool.id,
        type_=K8S_WORKERPOOL,
        request_payload=json.dumps(data)
    )
    doosradb.session.add(task)
    doosradb.session.commit()

    task_create_ibm_k8s_workerpool.delay(
        task_id=task.id,
        cloud_id=cloud.id,
        region=vpc.region,
        k8s_workerpool_id=k8s_workerpool.id
    )

    LOGGER.info("".format(user.email))
    resp = jsonify({
        "task_id": task.id,
        "resource_id": k8s_workerpool.id,
    })

    resp.status_code = 202
    return resp


@ibm_k8s.route('/k8s/k8s_clusters/kube_versions', methods=['GET'])
@authenticate
def get_k8s_kube_versions(user_id, user):
    """
    Get latest Kube Versions from IBM
    :param user: object of the user initiating the request
    :param user_id: ID of the user initiating the request
    :return: Response Task object of cluster
    """
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(project_id=user.project.id)
            .first()
    )
    if not cloud:
        LOGGER.info(
            "No IBM cloud found with Project ID {id}".format(id=user.project.id)
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not cloud.service_credentials:
        return Response("ERROR_COS_CREDENTIALS_MISSING", status=400)

    k8s_client = K8sClient(cloud.id)
    k8s_kube_versions = k8s_client.get_k8s_kube_versions()

    kube_versions = {}
    openshift_versions = []
    k8s_versions =[]

    if not k8s_kube_versions:
        return Response("ERROR_FINDING_IBM_KUBE_VERSIONS", status=404)

    # Kubernetes Kube Versions
    for kubernetes in k8s_kube_versions["kubernetes"]:
        kube ={}
        version  = "{}.{}.{}".format(kubernetes["major"],kubernetes["minor"] ,kubernetes["patch"])
        kube["version"] = version
        kube["default"] = kubernetes["default"]
        kube["end_of_service"] = kubernetes["end_of_service"]
        k8s_versions.append(kube)
    kube_versions["kubernetes"] = sorted(k8s_versions, key=lambda i: i['version'], reverse=True)
    # Openshift Kube Version
    for openshift in k8s_kube_versions["openshift"]:
        kube = {}
        version  = "{}.{}.{}".format(openshift["major"],openshift["minor"] ,openshift["patch"])
        kube["version"] = version
        kube["default"] = openshift["default"]
        kube["end_of_service"] = openshift["end_of_service"]
        openshift_versions.append(kube)
    kube_versions["openshift"] = sorted(openshift_versions, key=lambda i: i['version'], reverse=True)

    return Response(json.dumps(kube_versions), status=200)


@ibm_k8s.route('/k8s/k8s_clusters/worker_flavors/types/<type>/zones/<zone>', methods=['GET'])
@authenticate
def get_cluster_worker_flavors(user_id, user, type, zone):
    """
    Get Worker Machine Flavors of zones from IBM
    :param user: object of the user initiating the request
    :param user_id: ID of the user initiating the request
    :return: Response object of zone worker flavors
    """
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(project_id=user.project.id)
            .first()
    )
    if not cloud:
        LOGGER.info(
            "No IBM cloud found with Project ID {id}".format(id=user.project.id)
        )
        return Response("Cloud not Found" ,status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not cloud.service_credentials:
        return Response("ERROR_COS_CREDENTIALS_MISSING", status=400)

    if type not in ["openshift", "kubernetes"]:
        return Response("ERROR_WRONG_CLUSTER_TYPE", status=404)

    k8s_client = K8sClient(cloud.id)
    ibm_locations = k8s_client.get_all_locations()
    
    if not ibm_locations:
        return Response("ERROR_GETTING_IBM_LOCATIONS", status=500)

    zone_flavors_for_openshift = []
    zone_locations = []
    for location in ibm_locations:
        if location.get("kind") == "zone":
            zone_locations.append(location["id"])

    if zone not in zone_locations:
        return Response("ERROR_INVALID_ZONE_NAME", status=404)

    k8s_zone_flavors = k8s_client.list_k8s_zone_flavours(zone, "vpc-gen2")

    if not k8s_zone_flavors:
        return Response("ERROR_WORKER_FLAVORS_NOT_FOUND", status=404)

    if type != "openshift":
        flavors = sorted(k8s_zone_flavors, key=lambda i: (i['name'].split("x")[0], i['cores'],i['memory'].split("G")[0]))
        return Response(json.dumps(flavors), status=200, mimetype="application/json")


    for zone_flavor in k8s_zone_flavors:
        memory = zone_flavor.get("memory").split("GB")

        if int(zone_flavor.get("cores")) >= 4 and int(memory[0]) >= 16:
            zone_flavor["os"] = OPENSHIFT_OS
            zone_flavors_for_openshift.append(zone_flavor)

    flavors = sorted(zone_flavors_for_openshift, key=lambda i: (i['name'].split("x")[0], i['cores'], i['memory'].split("G")[0]))

    return Response(json.dumps(flavors), status=200,mimetype="application/json")


@ibm_k8s.route('/k8s/k8s_clusters/tasks/<task_id>', methods=['GET'])
@authenticate
def get_add_k8s_cluster_task(user_id, user, task_id):
    """
    Get Create k8s Cluster (kubernetes or Openshift) Task
    :param user: object of the user initiating the request
    :param user_id: ID of the user initiating the request
    :return: Response Task object of cluster
    """
    cluster_creation_task = doosradb.session.query(IBMTask).filter_by(id=task_id).first()
    if not cluster_creation_task:
        LOGGER.info(f"No CLUSTER CREATION task found with ID {task_id}")
        return Response(status=404)

    doosra_k8s_cluster = doosradb.session.query(KubernetesCluster).filter_by(id=cluster_creation_task.resource_id).first()
    if not doosra_k8s_cluster:
        if cluster_creation_task.action == 'DELETE' and cluster_creation_task.status in ['SUCCESS', 'CREATED']:
            return Response(status=200)
        LOGGER.info("No KubernetesCluster found for ID: {}".format(cluster_creation_task.resource_id))
        return Response(status=404)

    return Response(json.dumps(doosra_k8s_cluster.to_json()), status=200, mimetype="application/json")


@ibm_k8s.route('/k8s/k8s_clusters', methods=['POST'])
@validate_json(ibm_add_kubernetes_cluster_schema)
@authenticate
def add_k8s_cluster(user_id, user):
    """
    Create k8s Cluster (kubernetes or Openshift)
    :param user: object of the user initiating the request
    :param user_id: ID of the user initiating the request
    :return: Response object of task_id and resource_id of created cluster
    """
    from doosra.tasks.ibm.kubernetes_tasks import task_create_ibm_k8s_cluster

    data = request.get_json(force=True)
    cloud = (
        doosradb.session.query(IBMCloud)
            .filter_by(project_id=user.project.id)
            .first()
    )
    if not cloud:
        LOGGER.info(
            "No IBM cloud found with ID {id}".format(id=data["cloud_id"])
        )
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not cloud.service_credentials:
        return Response("ERROR_COS_CREDENTIALS_MISSING", status=400)

    # CHECK FOR CREATING CLUSTER NAME CONFLICT
    k8s_client = K8sClient(cloud.id)
    k8s_clusters = k8s_client.list_k8s_cluster(provider="ALL")
    if not k8s_clusters:
        return Response("ERROR_K8S_CLUSTERS_NOT_FOUND", status=404)

    for k8s_cluster in k8s_clusters:
        if data["name"] == k8s_cluster["name"]:
            return Response("ERROR_CONFLICTING_CLUSTER_NAME", status=409)

    cluster = (
        doosradb.session.query(KubernetesCluster)
            .filter_by(name=data['name'], cloud_id=cloud.id)
            .first()
    )
    if cluster:
        return Response("ERROR_CONFLICTING_CLUSTER_NAME", status=409)

    vpc = (
        doosradb.session.query(IBMVpcNetwork)
            .filter_by(id=data['vpc_id'], cloud_id=cloud.id)
            .first()
    )
    if not vpc:
        LOGGER.info("No IBM VPC found with ID {id}".format(id=data['vpc_id']))
        return Response(status=404)

    subnets = (
        doosradb.session.query(IBMSubnet)
            .filter_by(vpc_id=vpc.id)
            .all()
    )
    if not subnets:
        LOGGER.info("No IBM SUBNETS found within VPC ID {id}".format(id=data['vpc_id']))
        return Response(status=404)

    if data["type"] not in ["openshift", "kubernetes"]:
        return Response("ERROR_WRONG_CLUSTER_TYPE ", status=404)

    if data["type"] == "openshift":
        data["kube_version"] = data.get("kube_version") + "_openshift"

    k8s_cluster = KubernetesCluster(
        name=data["name"],
        disable_public_service_endpoint=False,
        kube_version= data["kube_version"],
        pod_subnet=data.get('pod_subnet'),
        provider=data["provider"],
        service_subnet=data.get('service_subnet'),
        status=CREATION_PENDING,
        state=CLUSTER_REQUESTED,
        cluster_type=data["type"],
        cloud_id=cloud.id,
    )
    k8s_cluster.ibm_vpc_network = vpc
    k8s_cluster.ibm_resource_group = vpc.ibm_resource_group

    worker_pools = data["worker_pools"]
    for worker_pool in worker_pools:
        k8s_cluster_worker_pool = KubernetesClusterWorkerPool(
            name=worker_pool["name"],
            disk_encryption=worker_pool['disk_encryption'],
            flavor=worker_pool['flavor'],
            worker_count=worker_pool['worker_count'],
        )

        for worker_pool_zone in worker_pool["zones"]:
            k8s_cluster_worker_pool_zone = KubernetesClusterWorkerPoolZone(
                name=worker_pool_zone["name"]
            )
            for subnet in subnets:
                if subnet.name == worker_pool_zone["subnet"]:
                    k8s_cluster_worker_pool_zone.subnets.append(subnet)
            k8s_cluster_worker_pool.zones.append(k8s_cluster_worker_pool_zone)
        k8s_cluster.worker_pools.append(k8s_cluster_worker_pool)
    doosradb.session.add(k8s_cluster)

    # Create Task for Creation of Cluster
    task = IBMTask(
        region=data.get("region"),
        task_id=None,
        action="ADD",
        cloud_id=cloud.id,
        resource_id=k8s_cluster.id,
        type_=K8S_CLUSTER,
        request_payload=json.dumps(data)
    )
    doosradb.session.add(task)
    doosradb.session.commit()

    task_create_ibm_k8s_cluster.delay(
        task_id=task.id,
        cloud_id=cloud.id,
        region=data['region'],
        k8s_cluster_id=k8s_cluster.id,
    )

    LOGGER.info(CLUSTER_CREATE.format(user.email))
    resp = jsonify({
        "task_id": task.id,
        "resource_id": k8s_cluster.id,
    })
    resp.status_code = 202
    return resp


@ibm_k8s.route('/k8s/k8s_clusters/<k8s_cluster_id>', methods=['DELETE'])
@authenticate
def delete_ibm_k8s_cluster(user_id, user, k8s_cluster_id):
    """
    Delete an IBM K8S Cluster
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param k8s_cluster_id: k8s_cluster_id for K8S cluster
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.kubernetes_tasks import task_delete_ibm_k8s_cluster_workflow

    k8s_cluster = doosradb.session.query(KubernetesCluster).filter_by(id=k8s_cluster_id).first()
    if k8s_cluster.status in ['PENDING', 'IN_PROGRESS', 'CREATING', 'CREATION_PENDING']:
        LOGGER.info("IBM K8S Cluster Migration in Progress with ID {id}".format(id=k8s_cluster_id))
        return Response(status=405)

    if not k8s_cluster:
        LOGGER.info("No IBM K8S Cluster found with ID {id}".format(id=k8s_cluster_id))
        return Response(status=404)

    if k8s_cluster.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not k8s_cluster.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="K8S_CLUSTER", region=k8s_cluster.ibm_vpc_network.region, action="DELETE",
        cloud_id=k8s_cluster.ibm_cloud.id, resource_id=k8s_cluster.id)

    doosradb.session.add(task)
    k8s_cluster.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_k8s_cluster_workflow.delay(task_id=task.id, cloud_id=k8s_cluster.ibm_cloud.id,
                                               region=k8s_cluster.ibm_vpc_network.region,
                                               k8s_cluster_id=k8s_cluster.id)

    LOGGER.info(K8S_CLUSTER_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp

