import logging
import traceback

from doosra import db as doosradb
from doosra.ibm.managers.exceptions import *
from doosra.models.ibm.kubernetes_models import KubernetesCluster, KubernetesClusterWorkerPool
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.common.consts import CREATED, ERROR_CREATING, CREATING
from doosra.ibm.kubernetes.consts import CLUSTER_NORMAL, CLUSTER_DEPLOYING
from doosra.ibm.clouds.consts import FAILURE

LOGGER = logging.getLogger("k8s_tasks.py")


def create_ibm_k8s_cluster(ibm_manager, k8s_cluster_id):
    """
    This request Creates a K8s Cluster for IBM cloud and handles the exceptions
    :return:
    """
    LOGGER.info("Task ibm k8s creation for cluster: {k8s_cluster} initiated".format(k8s_cluster=k8s_cluster_id))

    k8s_cluster = doosradb.session.query(KubernetesCluster).filter_by(id=k8s_cluster_id).first()
    if not k8s_cluster:
        LOGGER.info("No KubernetesCluster found for ID: {}".format(k8s_cluster_id))
        return
    configured_k8s_cluster = dict()
    try:
        k8s_cluster.status = CREATING
        k8s_cluster.state = CLUSTER_DEPLOYING
        configured_k8s_cluster = configure_and_save_obj_confs(ibm_manager, k8s_cluster)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError, Exception) as ex:
        LOGGER.info(f"K8s CLUSTER with ID {k8s_cluster_id} GOT EXCEPTION")
        LOGGER.info(ex)
        traceback.print_exc()

        if k8s_cluster:
            k8s_cluster.status = ERROR_CREATING
            k8s_cluster.state = FAILURE
        doosradb.session.commit()

    else:
        k8s_cluster.status = CREATED
        k8s_cluster.state = CLUSTER_NORMAL
        k8s_cluster.pod_subnet = configured_k8s_cluster.pod_subnet
        k8s_cluster.service_subnet = configured_k8s_cluster.service_subnet
        k8s_cluster.kube_version = configured_k8s_cluster.kube_version
        LOGGER.info(f"k8s CLUSTER NAME {configured_k8s_cluster.name} CREATED")
        doosradb.session.commit()

    return configured_k8s_cluster


def create_ibm_k8s_workerpool(ibm_manager, k8s_workerpool_id):
    """
    This request Creates a K8s Workerpool for given Cluster for IBM cloud
    :return:
    """
    LOGGER.info("Task ibm k8s creation for Workerpool ID: {k8s_workerpool} initiated".format(k8s_workerpool=k8s_workerpool_id))
    configured_k8s_workerpool = None

    k8s_workerpool = doosradb.session.query(KubernetesClusterWorkerPool).filter_by(id=k8s_workerpool_id).first()
    if not k8s_workerpool:
        LOGGER.info("No KubernetesCluster found for ID: {}".format(k8s_workerpool_id))
        return
    try:
        configured_k8s_workerpool = configure_and_save_obj_confs(ibm_manager, k8s_workerpool)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError, Exception) as ex:
        LOGGER.info(f"K8s CLUSTER WORKERPOOL ID {k8s_workerpool_id} GOT EXCEPTION:")
        LOGGER.info(ex)
        doosradb.session.delete(k8s_workerpool)
        doosradb.session.commit()
    else:
        k8s_workerpool.resource_id = configured_k8s_workerpool.resource_id
        LOGGER.info(f"K8s CLUSTER WORKERPOOL NAME {k8s_workerpool.name} CREATED")
        doosradb.session.commit()

    return configured_k8s_workerpool
