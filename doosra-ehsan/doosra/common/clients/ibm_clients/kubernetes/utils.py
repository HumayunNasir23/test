import json
import logging
from datetime import datetime

from kubernetes import client
from kubernetes.client import Configuration
from kubernetes.client.rest import ApiException
from kubernetes.config import kube_config
from urllib3.exceptions import ConnectTimeoutError, MaxRetryError, NewConnectionError

from doosra import db as doosradb
from doosra.common.clients.ibm_clients.kubernetes.consts import BACKUP_CRD, BACKUP_STORAGE_CRD, DELETE_BACKUP_REQ_CRD, \
    DOWNLOAD_REQ_CRD, POD_VOLUME_RESTORE_CRD, POD_VOLUME_BACKUP_CRD, RESTIC_REPO_CRD, RESTORE_CRD, SCHEDULE_CRD, \
    SERVER_STATUS_CRD, VOLUME_SNAPSHOT_CRD, VELERO_NS, VELERO_CRB, VELERO_SERVICE_ACCOUNT, VELERO_SECRET, \
    BACKUP_STORAGE, VELERO_DEPLOYMENT, RESTIC_DAEMONSET
from doosra.common.utils import decrypt_api_key
from doosra.models.migration_models import KubernetesClusterMigrationTask

LOGGER = logging.getLogger("utils.py")


class K8s(object):
    def __init__(self, configuration_json):
        self.configuration_json = configuration_json

    @property
    def client(self):
        k8_loader = kube_config.KubeConfigLoader(self.configuration_json)
        call_config = type.__call__(Configuration)
        k8_loader.load_and_set(call_config)
        Configuration.set_default(call_config)
        return client


def deploy_velero_and_get_backup_restore(kube_config, task_type, backup_name=None, restore_name=None):
    creation_time_stamp = datetime.utcnow()
    while True:
        try:
            if task_type == "DEPLOY":
                list_daemon_set = kube_config.client.AppsV1Api().list_namespaced_daemon_set("velero", pretty=True)
                list_deployment = kube_config.client.AppsV1Api().list_namespaced_deployment("velero", pretty=True)
                if (datetime.utcnow() - creation_time_stamp).seconds < 180:
                    for daemon_set in list_daemon_set.items:
                        if daemon_set.status.current_number_scheduled == daemon_set.status.number_ready:
                            for deployment in list_deployment.items:
                                if deployment.status.ready_replicas == deployment.status.replicas:
                                    return True
                else:
                    return False

            elif task_type == "BACKUP":
                get_backup = kube_config.client.CustomObjectsApi().get_namespaced_custom_object(group="velero.io",
                                                                                                version="v1",
                                                                                                namespace="velero",
                                                                                                plural="backups",
                                                                                                name=backup_name)
                if get_backup.get('status', {}).get('phase') == "Completed":
                    return True
                if get_backup.get('status', {}).get('phase') in ["Failed", "PartiallyFailed", "FailedValidation"]:
                    return False
                if not get_backup:
                    return False

            else:
                get_restore = kube_config.client.CustomObjectsApi().get_namespaced_custom_object(group="velero.io",
                                                                                                 version="v1",
                                                                                                 namespace="velero",
                                                                                                 plural="restores",
                                                                                                 name=restore_name)
                if get_restore.get('status', {}).get('phase') in ["Completed", "PartiallyFailed"]:
                    return True
                if get_restore.get('status', {}).get('phase') in ["Failed", "FailedValidation"]:
                    return False
                if not get_restore:
                    return False

        except (ApiException, ConnectTimeoutError, MaxRetryError, NewConnectionError) as error:
            if isinstance(error, ApiException):
                if error.status == 404:
                    continue
                else:
                    return False


def deploy_velero_agent(cluster_migration_task_id, config=None):
    try:
        k8s_cluster_migration_task = doosradb.session.query(KubernetesClusterMigrationTask). \
            filter_by(id=cluster_migration_task_id).first()

        if config == "source":
            kube_config = K8s(configuration_json=k8s_cluster_migration_task.source_cluster)
        else:
            kube_config = K8s(configuration_json=k8s_cluster_migration_task.target_cluster)
        cos_secret = k8s_cluster_migration_task.cos

        LOGGER.info("Deploying Velero CRDs")
        custom_resource_definitions = [BACKUP_CRD, BACKUP_STORAGE_CRD, DELETE_BACKUP_REQ_CRD,
                                       DOWNLOAD_REQ_CRD, POD_VOLUME_RESTORE_CRD,
                                       POD_VOLUME_BACKUP_CRD, RESTIC_REPO_CRD, RESTORE_CRD, SCHEDULE_CRD,
                                       SERVER_STATUS_CRD, VOLUME_SNAPSHOT_CRD]
        for custom_resource_definition in custom_resource_definitions:
            body = json.loads(custom_resource_definition)
            try:
                kube_config.client.ApiextensionsV1beta1Api().create_custom_resource_definition(body=body)
            except ApiException as error:
                if error.status == 409:
                    pass

        body = json.loads(VELERO_NS)
        try:
            LOGGER.info("Creating Velero namespace")
            kube_config.client.CoreV1Api().create_namespace(body=body)
        except ApiException as error:
            if error.status == 409:
                pass

        body = json.loads(VELERO_CRB)
        try:
            LOGGER.info("Creating Velero Custom Role Binding")
            kube_config.client.RbacAuthorizationV1beta1Api().create_cluster_role_binding(body=body)
        except ApiException as error:
            if error.status == 409:
                pass

        body = json.loads(VELERO_SERVICE_ACCOUNT)
        try:
            LOGGER.info("Creating Velero Service Account")
            kube_config.client.CoreV1Api().create_namespaced_service_account(body=body, namespace="velero")
        except ApiException as error:
            if error.status == 409:
                pass

        LOGGER.info("Creating Velero Secret")
        body = json.loads(VELERO_SECRET)
        body['stringData']['cloud'] = f"[default]\naws_access_key_id:" \
                                      f"{decrypt_api_key(cos_secret['access_key_id'])}\naws_secret_access_key:" \
                                      f"{decrypt_api_key(cos_secret['secret_access_key'])}\n "
        try:
            kube_config.client.CoreV1Api().create_namespaced_secret(body=body, namespace="velero")
        except ApiException as error:
            if error.status == 409:
                pass

        body = json.loads(BACKUP_STORAGE)
        body['spec']['config']['region'] = cos_secret['bucket_region']
        body['spec']['config'][
            's3Url'] = f"https://s3.{cos_secret['bucket_region']}.cloud-object-storage.appdomain.cloud"
        body['spec']['objectStorage']['bucket'] = cos_secret['bucket_name']
        try:
            LOGGER.info("Creating Custom Resource Backup")
            kube_config.client.CustomObjectsApi().create_namespaced_custom_object(body=body, group="velero.io",
                                                                                  namespace="velero", version="v1",
                                                                                  plural="backupstoragelocations")
        except ApiException as error:
            if error.status == 409:
                pass

        body = json.loads(VELERO_DEPLOYMENT)
        try:
            LOGGER.info("Deploying Velero")
            kube_config.client.AppsV1Api().create_namespaced_deployment(body=body, namespace="velero")
        except ApiException as error:
            if error.status == 409:
                pass

        body = json.loads(RESTIC_DAEMONSET)
        try:
            LOGGER.info("Deploying Restic")
            kube_config.client.AppsV1Api().create_namespaced_daemon_set(body=body, namespace="velero")
        except ApiException as error:
            if error.status == 409:
                pass

        velero_status = deploy_velero_and_get_backup_restore(kube_config=kube_config, task_type="DEPLOY")

        if velero_status:
            LOGGER.info("Velero manifests deployed Successfully")
            return True

        else:
            LOGGER.info("Velero failed to deploy")
            return False

    except ApiException as error:
        LOGGER.info(f"Failed due to {error.reason} : status code {error.status}")
        return
