import base64
import logging
import time
from datetime import datetime

from celery import chain
from flask import Response
from kubernetes import client
from kubernetes.client.rest import ApiException
from urllib3.exceptions import MaxRetryError, ConnectTimeoutError

from doosra import db as doosradb
from doosra.common.clients.ibm_clients import K8sClient
from doosra.common.clients.ibm_clients.exceptions import *
from doosra.common.clients.ibm_clients.kubernetes.consts import CREATE_BACKUP_TEMPLATE, CREATE_RESTORE_TEMPLATE, \
    BUCKET_CREATION_ERROR, VELERO_INSTALLATION_FAILED, BACKUP_CRD, BACKUP_STORAGE_CRD, \
    DELETE_BACKUP_REQ_CRD, DOWNLOAD_REQ_CRD, POD_VOLUME_RESTORE_CRD, POD_VOLUME_BACKUP_CRD, RESTIC_REPO_CRD, \
    RESTORE_CRD, SCHEDULE_CRD, SERVER_STATUS_CRD, VOLUME_SNAPSHOT_CRD, CLEANUP_CLUSTER, \
    COS_SERVICE_ACCOUNTS, COS_CLUSTER_ROLES, COS_CLUSTER_ROLE_BINDING, COS_DRIVER_DAEMONSET, COS_PLUGIN_DEPLOYMENT, \
    COS_STORAGE_CLASSES, CLASSIC_BLOCK_STORAGE_CLASSES, COS_PVC, BLOCK_STORAGE_PVC
from doosra.common.clients.ibm_clients.kubernetes.kubernetes import VPCKubernetesClient, ClassicKubernetesClient
from doosra.common.clients.ibm_clients.kubernetes.utils import K8s
from doosra.common.clients.ibm_clients.kubernetes.utils import deploy_velero_and_get_backup_restore, \
    deploy_velero_agent
from doosra.common.consts import IN_PROGRESS, CREATED, SUCCESS, FAILED
from doosra.common.utils import DELETING, DELETED
from doosra.common.utils import decrypt_api_key
from doosra.ibm.common.consts import PROVISIONING, VALIDATION
from doosra.ibm.managers import IBMManager
from doosra.ibm.managers.exceptions import IBMInvalidRequestError
from doosra.models import (
    SoftlayerCloud,
    IBMCloud,
    IBMTask,
    KubernetesCluster
)
from doosra.models.migration_models import KubernetesClusterMigrationTask
from doosra.tasks import WorkflowTerminated
from doosra.tasks.celery_app import celery
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_ibm_task

LOGGER = logging.getLogger("k8s_tasks.py")


@celery.task(name="task_get_k8s_cluster_workloads", base=IBMBaseTask, bind=True)
def task_get_k8s_cluster_workloads(self, task_id, cloud_id, region, k8s_cluster_resource_id):
    """
    Get Kubernetes Cluster Workloads
    :return:
    """
    k8s_client = K8sClient(cloud_id)
    kube_config = k8s_client.get_k8s_cluster_kube_config(cluster=k8s_cluster_resource_id)
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

    k8s_cluster = (
        doosradb.session.query(KubernetesCluster)
            .filter_by(resource_id=k8s_cluster_resource_id, cloud_id=cloud_id)
            .first()
    )
    if k8s_cluster:
        k8s_cluster.workloads = json.dumps(k8s_workloads)
        doosradb.session.commit()
        del k8s_workloads


@celery.task(name="create_ibm_k8s_workerpool", base=IBMBaseTask, bind=True)
def task_create_ibm_k8s_workerpool(self, task_id, cloud_id, region, k8s_workerpool_id):
    """
    Create the K8s Workerpool for Kubernetes Cluster workflow for k8s tasks and it's status update
    :return:
    """
    from doosra.ibm.kubernetes.utils import create_ibm_k8s_workerpool
    time.sleep(1)
    k8s_workerpool = create_ibm_k8s_workerpool(self.ibm_manager, k8s_workerpool_id)

    task = (
        doosradb.session.query(IBMTask)
            .filter_by(id=task_id)
            .first()
    )

    if task and k8s_workerpool:
        task.status = SUCCESS
        task.resource_id = k8s_workerpool.id
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="create_ibm_k8s_cluster", base=IBMBaseTask, bind=True)
def task_create_ibm_k8s_cluster(self, task_id, region, cloud_id, k8s_cluster_id):
    """
    Create the workflow for Kubernetes and Openshift Cluster
    :return:
    """
    from doosra.ibm.kubernetes.utils import create_ibm_k8s_cluster
    k8s_cluster = create_ibm_k8s_cluster(self.ibm_manager, k8s_cluster_id)

    task = (
        doosradb.session.query(IBMTask)
            .filter_by(id=task_id)
            .first()
    )

    if task and k8s_cluster:
        task.status = SUCCESS
    elif task:
        task.status = FAILED
    doosradb.session.commit()


@celery.task(name="task_delete_ibm_k8s_cluster_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_k8s_cluster_workflow(self, task_id, cloud_id, region, k8s_cluster_id):
    """
    This request is workflow for the K8S Cluster deletion
    @return:
    """

    workflow_steps = list()

    ibm_k8s_cluster = doosradb.session.query(KubernetesCluster).filter_by(id=k8s_cluster_id).first()
    if not ibm_k8s_cluster:
        return

    workflow_steps.append(task_delete_ibm_k8s_cluster.si(task_id=task_id, cloud_id=cloud_id,
                                                         region=region,
                                                         k8s_cluster_id=k8s_cluster_id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="task_delete_ibm_k8s_cluster", base=IBMBaseTask, bind=True)
def task_delete_ibm_k8s_cluster(self, task_id, cloud_id, region, k8s_cluster_id):
    """
    This request deletes an K8S Cluster and its attached resources
    @return:
    """
    ibm_k8s_cluster = doosradb.session.query(KubernetesCluster).filter_by(id=k8s_cluster_id).first()
    if not ibm_k8s_cluster:
        return

    self.resource = ibm_k8s_cluster
    ibm_k8s_cluster.status = DELETING
    doosradb.session.commit()

    fetched_k8s_cluster = self.ibm_manager.rias_ops.fetch_ops.get_all_k8s_clusters(
        name=ibm_k8s_cluster.name, vpc=ibm_k8s_cluster.ibm_vpc_network.name
    )
    if fetched_k8s_cluster:
        self.ibm_manager.rias_ops.delete_ibm_k8s_cluster(fetched_k8s_cluster[0])

    ibm_k8s_cluster.status = DELETED
    doosradb.session.delete(ibm_k8s_cluster)
    doosradb.session.commit()
    LOGGER.info("IBM K8S Cluster '{name}' deleted successfully on IBM Cloud".format(name=ibm_k8s_cluster.name))


@celery.task(name="validate_kubernetes_cluster", base=IBMBaseTask, bind=True)
def task_validate_kubernetes_cluster(self, task_id, cloud_id, region, cluster_id):
    """ Check if Cluster already exists """

    cluster = doosradb.session.query(KubernetesCluster).filter_by(id=cluster_id).first()
    if not cluster:
        LOGGER.info("No IKS Cluster found with ID: {}".format(cluster_id))
        return Response(status=404)

    self.resource = cluster
    self.resource_type = "iks_clusters"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )

    kubernetes_client = VPCKubernetesClient(cloud_id)
    existing_cluster = kubernetes_client.get_cluster_status(cluster.name)
    if existing_cluster:
        raise IBMInvalidRequestError("IKS Cluster with name '{cluster}'"
                                     " already provisioned".format(cluster=cluster.name))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info("IKS Cluster with name '{cluster}' validated successfully".format(cluster=cluster.name))


@celery.task(name="migrate_kubernetes_cluster", base=IBMBaseTask, bind=True)
def task_migrate_kubernetes_cluster(self, task_id, cloud_id, region, cluster_id, source_cluster, softlayer_id):
    cluster = doosradb.session.query(KubernetesCluster).filter_by(id=cluster_id).first()
    if not cluster:
        LOGGER.info("No IKS Cluster found with ID: {}".format(cluster_id))
        return Response(status=404)

    softlayer_cloud = doosradb.session.query(SoftlayerCloud).filter_by(id=softlayer_id).first()
    if not softlayer_cloud:
        LOGGER.info("No Softlayer Cloud found with ID: {}".format(softlayer_id))
        return Response(status=404)

    source_k8s_client = ClassicKubernetesClient(softlayer_cloud.username, softlayer_cloud.api_key)
    cloud = doosradb.session.query(IBMCloud).filter_by(id=cloud_id).first()
    ibm_manager = IBMManager(cloud=cloud, region=region)
    backup_name = "backup" + str(datetime.utcnow().strftime("-%m-%d-%Y%H-%M-%S"))
    bucket = ibm_manager.cos_ops.create_bucket(cluster.name + cluster.id[:3], region)

    if bucket and bucket.get('ResponseMetadata', {}).get('HTTPStatusCode', {}) == 200:
        LOGGER.info("Bucket {} created successfully".format(cluster.name + cluster.id[:3]))

        cos = {
            "bucket_name": cluster.name + cluster.id[:3],
            "access_key_id": cloud.service_credentials.access_key_id,
            "secret_access_key": cloud.service_credentials.secret_access_key,
            "bucket_region": region
        }

        cluster_migration_task = KubernetesClusterMigrationTask(
            base_task_id=task_id, cos=cos,
            source_cluster=source_k8s_client.get_cluster_kube_config(cluster=source_cluster)
        )

        doosradb.session.add(cluster_migration_task)
        doosradb.session.commit()

        workflow_steps = list()
        workflow_steps.append(task_create_workload_backup.si(
            task_id=cluster_migration_task.base_task_id, region=region, cloud_id=cloud_id,
            cluster_migration_task_id=cluster_migration_task.id, cluster_id=cluster_id, backup_name=backup_name))
        workflow_steps.append(task_create_kubernetes_cluster.si(
            task_id=cluster_migration_task.base_task_id, region=region, cloud_id=cloud_id,
            cluster_migration_task_id=cluster_migration_task.id, cluster_id=cluster_id))
        workflow_steps.append(task_restore_workload_backup.si(
            task_id=cluster_migration_task.base_task_id, region=region, cloud_id=cloud_id,
            cluster_migration_task_id=cluster_migration_task.id, cluster_id=cluster_id, backup_name=backup_name))

        chain(workflow_steps).delay()

    else:
        doosradb.session.commit()
        LOGGER.info(BUCKET_CREATION_ERROR)
        raise WorkflowTerminated(BUCKET_CREATION_ERROR)


@celery.task(name="create_workload_backup", base=IBMBaseTask, bind=True)
def task_create_workload_backup(self, task_id, region, cloud_id, cluster_migration_task_id, cluster_id, backup_name):
    try:
        cluster = doosradb.session.query(KubernetesCluster).filter_by(id=cluster_id).first()
        if not cluster:
            LOGGER.info("No IKS Cluster found with ID: {}".format(cluster_id))
            return Response(status=404)

        kubernetes_cluster_migration_task = doosradb.session.query(KubernetesClusterMigrationTask).filter_by(
            id=cluster_migration_task_id).first()
        kube_config = K8s(configuration_json=kubernetes_cluster_migration_task.source_cluster)

        self.resource = cluster
        self.resource_type = "iks_clusters"
        cluster.status = IN_PROGRESS
        doosradb.session.commit()
        self.report_utils.update_reporting(
            task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
            status=IN_PROGRESS
        )

        self.report_path = ".cluster_migration"
        self.report_utils.update_reporting(
            task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
            status=IN_PROGRESS, path=self.report_path)

        self.report_path = ".cluster_migration.steps.backup"
        self.report_utils.update_reporting(
            task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
            status=IN_PROGRESS, path=self.report_path)

        deploy_velero = deploy_velero_agent(kubernetes_cluster_migration_task.id, "source")

        if deploy_velero:
            LOGGER.info("Creating workloads backup")
            body = json.loads(CREATE_BACKUP_TEMPLATE)
            body["metadata"]["name"] = backup_name
            kube_config.client.CustomObjectsApi().create_namespaced_custom_object(body=body, group="velero.io",
                                                                                  namespace="velero", version="v1",
                                                                                  plural="backups")

            backup = deploy_velero_and_get_backup_restore(kube_config=kube_config, task_type="BACKUP",
                                                          backup_name=backup_name)

            if backup:
                self.report_path = ".cluster_migration.steps.backup"
                self.report_utils.update_reporting(
                    task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                    stage=PROVISIONING, status=SUCCESS, path=self.report_path)
                LOGGER.info("Backup created successfully")
                task_cleanup_cluster.delay(kubernetes_cluster_migration_task.source_cluster)

            else:
                LOGGER.info("Backup Creation Failed")
                task_cleanup_cluster.delay(kubernetes_cluster_migration_task.source_cluster)
                raise WorkflowTerminated("Workloads Backup, Backup Creation Failed")

        else:
            LOGGER.info("Velero failed to deploy on source cluster")
            task_cleanup_cluster.delay(kubernetes_cluster_migration_task.source_cluster)
            raise WorkflowTerminated(VELERO_INSTALLATION_FAILED)

    except ApiException as error:
        LOGGER.info(f"Failed due to {error.reason} : status code {error.status}")
        return


@celery.task(name="create_kubernetes_cluster", base=IBMBaseTask, bind=True)
def task_create_kubernetes_cluster(self, task_id, region, cloud_id, cluster_migration_task_id, cluster_id):
    LOGGER.info("Task ibm kubernetes workflow for cluster: {cluster} initiated".format(cluster=cluster_id))
    cluster = doosradb.session.query(KubernetesCluster).filter_by(id=cluster_id).first()
    if not cluster:
        LOGGER.info("No IKS Cluster found with ID: {}".format(cluster_id))
        return Response(status=404)

    self.resource = cluster
    self.resource_type = "iks_clusters"
    cluster.status = IN_PROGRESS
    doosradb.session.commit()
    self.report_path = ".cluster_migration.steps.provisioning"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS, path=self.report_path)

    kubernetes_client = VPCKubernetesClient(cloud_id)
    provisioned_cluster = kubernetes_client.create_cluster(cluster)
    cluster.status = CREATED
    cluster.resource_id = provisioned_cluster
    doosradb.session.commit()

    self.report_path = ".cluster_migration.steps.provisioning"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS, path=self.report_path)

    k8s_cluster_migration_task = doosradb.session.query(KubernetesClusterMigrationTask).filter_by(
        id=cluster_migration_task_id).first()
    k8s_cluster_migration_task.target_cluster = kubernetes_client.get_cluster_kube_config(
        cluster_id=provisioned_cluster)
    doosradb.session.commit()

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=SUCCESS
    )


@celery.task(name="restore_workload_backup", base=IBMBaseTask, bind=True)
def task_restore_workload_backup(self, task_id, region, cloud_id, cluster_migration_task_id, cluster_id, backup_name):
    cluster_migration_task = doosradb.session.query(KubernetesClusterMigrationTask).filter_by(
        id=cluster_migration_task_id).first()

    if not cluster_migration_task:
        LOGGER.info("Migration Task Not Found")
        doosradb.session.commit()
        return Response(status=404)

    cluster = doosradb.session.query(KubernetesCluster).filter_by(id=cluster_id).first()
    if not cluster:
        LOGGER.info("No IKS Cluster found with ID: {}".format(cluster_id))
        return Response(status=404)

    self.resource = cluster
    self.resource_type = "iks_clusters"
    self.report_path = ".cluster_migration.steps.restore"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS, path=self.report_path)

    try:
        LOGGER.info(f"Migration task found for ID {cluster_migration_task.id}")
        deploy_velero = deploy_velero_agent(cluster_migration_task.id)

        if deploy_velero:
            LOGGER.info("Velero successfully deployed on cluster '{}'".format(cluster.name))

            source_config = K8s(configuration_json=cluster_migration_task.source_cluster)
            target_config = K8s(configuration_json=cluster_migration_task.target_cluster)

            restore_name = "restore" + str(datetime.utcnow().strftime("-%m-%d-%Y%H-%M-%S"))
            backup = deploy_velero_and_get_backup_restore(kube_config=target_config, task_type="BACKUP",
                                                          backup_name=backup_name)

            if backup:
                LOGGER.info("Restore In Progress")
                self.report_path = ".cluster_migration.steps.restore"
                self.report_utils.update_reporting(
                    task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                    stage=PROVISIONING, status=IN_PROGRESS, path=self.report_path)

                LOGGER.info("Discovering source cluster PVC's")
                pvcs = source_config.client.CoreV1Api().list_persistent_volume_claim_for_all_namespaces(watch=False)

                if pvcs.items:
                    pvcs_list = list()
                    object_storage = False
                    cos_secret = cluster_migration_task.cos
                    access_key = decrypt_api_key(cos_secret["access_key_id"])
                    secret_key = decrypt_api_key(cos_secret["secret_access_key"])

                    access_key_bytes = access_key.encode('ascii')
                    secret_key_bytes = secret_key.encode('ascii')

                    access_key_base64_bytes = base64.b64encode(access_key_bytes)
                    secret_key_base64_bytes = base64.b64encode(secret_key_bytes)

                    access_key = access_key_base64_bytes.decode('ascii')
                    secret_key = secret_key_base64_bytes.decode('ascii')

                    for pvc in pvcs.items:
                        if pvc.metadata.annotations['volume.beta.kubernetes.io/storage-provisioner'] ==\
                                "ibm.io/ibmc-file":
                            LOGGER.info("Discovering PVC's with File Storage Classes")

                            body = json.loads(COS_PVC)
                            body['metadata']['name'] = pvc.metadata.name
                            body['metadata']['namespace'] = pvc.metadata.namespace
                            body['metadata']['annotations']['ibm.io/bucket'] = \
                                "bucket" + str(datetime.utcnow().strftime("-%m-%d-%Y-%H-%M-%S"))
                            body['spec']['accessModes'] = pvc.spec.access_modes
                            body['spec']['resources']['requests']['storage'] = pvc.spec.resources.requests['storage']
                            pvcs_list.append(body)

                        elif pvc.metadata.annotations['volume.beta.kubernetes.io/storage-provisioner'] == \
                                "ibm.io/ibmc-block":
                            LOGGER.info("Discovering PVC's with Block Storage Classes")
                            body = json.loads(BLOCK_STORAGE_PVC)
                            for classic_block_storage_class in CLASSIC_BLOCK_STORAGE_CLASSES:
                                if pvc.spec.storage_class_name == classic_block_storage_class:
                                    body['metadata']['name'] = pvc.metadata.name
                                    body['metadata']['namespace'] = pvc.metadata.namespace
                                    body['spec']['accessModes'] = pvc.spec.access_modes
                                    body['spec']['resources']['requests']['storage'] = pvc.spec.resources.requests[
                                        'storage']
                                    body['spec']['storageClassName'] = "ibmc-vpc-block-10iops-tier"

                                else:
                                    body['metadata']['name'] = pvc.metadata.name
                                    body['metadata']['namespace'] = pvc.metadata.namespace
                                    body['spec']['accessModes'] = pvc.spec.access_modes
                                    body['spec']['resources']['requests']['storage'] = pvc.spec.resources.requests[
                                        'storage']
                                    body['spec']['storageClassName'] = "ibmc-vpc-block-custom"

                            pvcs_list.append(body)

                    LOGGER.info("Creating Namespaces On Provisioned Cluster")
                    for namespace in pvcs_list:
                        try:
                            target_config.client.CoreV1Api().create_namespace(
                                client.V1Namespace(metadata=client.V1ObjectMeta(
                                    name=namespace['metadata']['namespace'])
                                )
                            )
                        except ApiException as error:
                            if error.status == 409:
                                continue

                        if namespace['spec']['storageClassName'] == "ibmc-s3fs-standard-regional":

                            object_storage = True
                            secret = client.V1Secret(
                                api_version='v1',
                                metadata=client.V1ObjectMeta(
                                    name='cos-write-access',
                                    namespace=namespace['metadata']['namespace']
                                ),
                                kind='Secret',
                                type='ibm/ibmc-s3fs',
                                data={
                                    'access-key': access_key,
                                    'secret-key': secret_key
                                }
                            )

                            try:
                                target_config.client.CoreV1Api().create_namespaced_secret(
                                    body=secret, namespace=namespace['metadata']['namespace'])
                            except ApiException as error:
                                if error.status == 409:
                                    pass

                    if object_storage:
                        LOGGER.info("Deploying COS-Driver & COS-Plugin")

                        try:
                            target_config.client.CoreV1Api().create_namespace(
                                client.V1Namespace(metadata=client.V1ObjectMeta(name="ibm-object-s3fs")))
                        except ApiException as error:
                            if error.status == 409:
                                pass

                        for service_account in COS_SERVICE_ACCOUNTS:
                            body = json.loads(service_account)
                            try:
                                LOGGER.info("Creating Cloud Object Storage Service Account")
                                target_config.client.CoreV1Api().create_namespaced_service_account(
                                    body=body, namespace="ibm-object-s3fs")
                            except ApiException as error:
                                if error.status == 409:
                                    pass

                        for cluster_role in COS_CLUSTER_ROLES:
                            body = json.loads(cluster_role)
                            try:
                                LOGGER.info("Creating Cluster Role for Cloud Object Storage Plugin ")
                                target_config.client.RbacAuthorizationV1Api().create_cluster_role(body=body)
                            except ApiException as error:
                                if error.status == 409:
                                    pass

                        for cluster_role_binding in COS_CLUSTER_ROLE_BINDING:
                            body = json.loads(cluster_role_binding)
                            try:
                                LOGGER.info("Creating COS Custom Role Binding in Cluster")
                                target_config.client.RbacAuthorizationV1Api().create_cluster_role_binding(body=body)
                            except ApiException as error:
                                if error.status == 409:
                                    pass

                        body = json.loads(COS_DRIVER_DAEMONSET)
                        try:
                            LOGGER.info("Installing COS Driver Daemonset on Cluster")
                            target_config.client.AppsV1Api().create_namespaced_daemon_set(body=body,
                                                                                          namespace="ibm-object-s3fs")
                        except ApiException as error:
                            if error.status == 409:
                                pass

                        body = json.loads(COS_PLUGIN_DEPLOYMENT)
                        try:
                            LOGGER.info("Creating COS Deployment on Cluster")
                            target_config.client.AppsV1Api().create_namespaced_deployment(body=body,
                                                                                          namespace="ibm-object-s3fs")
                        except ApiException as error:
                            if error.status == 409:
                                pass

                        for cos_storage_class in COS_STORAGE_CLASSES:
                            body = json.loads(cos_storage_class)
                            if "REGION" in body['parameters']['ibm.io/object-store-endpoint']:
                                body['parameters'][
                                    'ibm.io/object-store-endpoint'] = \
                                    f"https://s3.direct.{region}.cloud-object-storage.appdomain.cloud"
                            try:
                                target_config.client.StorageV1Api().create_storage_class(body=body)
                            except ApiException as error:
                                if error.status == 409:
                                    pass

                    LOGGER.info("Creating Persistent Volume Claims in destination Cluster")
                    for pvc in pvcs_list:
                        try:
                            target_config.client.CoreV1Api().create_namespaced_persistent_volume_claim(
                                body=pvc, namespace=pvc['metadata']['namespace'])
                        except ApiException as error:
                            if error.status == 409:
                                pass

                    LOGGER.info("Waiting for PVC's to get binded with PV's")
                    time.sleep(60)

            else:
                raise WorkflowTerminated("RESTORE, Backup Not Found")

            body = json.loads(CREATE_RESTORE_TEMPLATE)
            body['metadata']['name'] = restore_name
            body["spec"]["backupName"] = backup_name
            target_config.client.CustomObjectsApi().create_namespaced_custom_object(body=body,
                                                                                    group="velero.io",
                                                                                    namespace="velero",
                                                                                    version="v1",
                                                                                    plural="restores")

            restore = deploy_velero_and_get_backup_restore(kube_config=target_config, task_type="RESTORE",
                                                           restore_name=restore_name)

            if restore:
                LOGGER.info(f"Updating migration status for migration id : {cluster_migration_task.id}")

                self.report_path = ".cluster_migration.steps.restore"
                self.report_utils.update_reporting(
                    task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                    stage=PROVISIONING, status=SUCCESS, path=self.report_path)

                self.report_path = ".cluster_migration"
                self.report_utils.update_reporting(
                    task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                    stage=PROVISIONING, status=SUCCESS, path=self.report_path)
                self.report_utils.update_reporting(
                    task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                    stage=PROVISIONING, status=SUCCESS)

                cluster_migration_task.message = f"successfully migrated {cluster_migration_task.id}"
                cluster_migration_task.completed_at = datetime.utcnow()
                doosradb.session.commit()
                LOGGER.info(f"migration completed Successfully {cluster_migration_task.id}")

            else:
                LOGGER.info("Restore creation failed")
                raise WorkflowTerminated("RESTORE, Restoration Failed")

            task_cleanup_cluster.delay(cluster_migration_task.target_cluster)

        else:
            LOGGER.info("Velero failed to deploy on migrated cluster")
            raise WorkflowTerminated("RESTORE, Restoration Failed, Please Check your Cluster internet Connectivity")

    except ApiException as error:
        LOGGER.info(error)
        cluster_migration_task.message = f"Failed due {error.reason} : status {error.status}"
        doosradb.session.commit()
        return


@celery.task(name="cleanup_cluster", bind=True)
def task_cleanup_cluster(self, kube_config):
    kube_config = K8s(kube_config)
    body = json.loads(CLEANUP_CLUSTER)
    kube_config.client.BatchV1Api().create_namespaced_job(namespace='velero', body=body)

    custom_resource_def = [BACKUP_CRD, BACKUP_STORAGE_CRD, DELETE_BACKUP_REQ_CRD, DOWNLOAD_REQ_CRD,
                           POD_VOLUME_RESTORE_CRD,
                           POD_VOLUME_BACKUP_CRD, RESTIC_REPO_CRD, RESTORE_CRD, SCHEDULE_CRD,
                           SERVER_STATUS_CRD,
                           VOLUME_SNAPSHOT_CRD]

    try:
        kube_config.client.CoreV1Api().delete_namespace(name='velero')
        kube_config.client.RbacAuthorizationV1beta1Api().delete_cluster_role_binding(name='velero')
        for CRD in custom_resource_def:
            body = json.loads(CRD)
            kube_config.client.ApiextensionsV1beta1Api().delete_custom_resource_definition(
                name=body['metadata']['name'])
        LOGGER.info(f"Velero removed from cluster")
    except (ApiException, MaxRetryError, ConnectTimeoutError) as error:
        LOGGER.info(error)
