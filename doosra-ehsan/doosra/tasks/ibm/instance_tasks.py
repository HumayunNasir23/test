import copy
import logging
import os

from celery import chain, chord, group

from doosra import db as doosradb
from doosra.common.clients.ibm_clients import ImagesClient, InstancesClient
from doosra.common.clients.ibm_clients.exceptions import IBMExecuteError as ClientIBMExecuteError
from doosra.common.consts import FAILED, IN_PROGRESS, SUCCESS, VALID
from doosra.common.utils import CREATED, CREATING, DELETED, DELETING, encrypt_api_key, return_cos_object_name, \
    return_vpc_image_name, transform_ibm_name
from doosra.common.utils import decrypt_api_key
from doosra.ibm.common.billing_utils import log_resource_billing
from doosra.ibm.common.consts import FLOATING_IP_NAME, INST_CREATING_CUSTOM_IMAGE, INST_CREATING_IMAGE_TEMPLATE, \
    INST_EXPORT_COS, INST_IMAGE_CONVERTING, INST_INSTANCE_CREATING, PROVISIONING, VALIDATION
from doosra.ibm.common.report_consts import *
from doosra.ibm.images.consts import COS_URI, IMAGE_TEMPLATE_PATH
from doosra.ibm.instances.consts import IBM_GEN2_WINDOWS_REQ_STRING, RESTORE_ADMIN_USER_DATA
from doosra.ibm.instances.utils import get_volume_name
from doosra.ibm.managers import IBMManager
from doosra.ibm.managers.exceptions import IBMAuthError, IBMBoto3ReadTimeoutError, IBMConnectError, IBMExecuteError, \
    IBMInvalidRequestError
from doosra.migration.data_migration.consts import *
from doosra.migration.data_migration.volume_extraction_utils import construct_user_data_script, \
    construct_nas_migration_user_data
from doosra.migration.managers.softlayer_manager import SoftLayerManager
from doosra.models import (IBMCloud, IBMFloatingIP, IBMImage, IBMInstance, IBMNetworkInterface, IBMSecurityGroup,
                           IBMSecurityGroupRule, IBMSshKey, IBMSubnet, IBMTask, IBMVolume, IBMVolumeAttachment,
                           IBMVolumeProfile, ImageConversionTask, SecondaryVolumeMigrationTask, SoftlayerCloud)
from doosra.models.ibm.instance_tasks_model import IBMInstanceTasks
from doosra.tasks.celery_app import celery
from doosra.tasks.exceptions import TaskFailureError
from doosra.tasks.ibm.base_tasks import IBMBaseTask, update_group_tasks, update_ibm_task
from doosra.tasks.ibm.floating_ip_tasks import task_create_ibm_floating_ip, task_delete_ibm_floating_ip
from doosra.tasks.ibm.image_conversion_tasks import get_image_size
from doosra.tasks.ibm.image_tasks import task_validate_ibm_images
from doosra.tasks.ibm.security_group_tasks import task_add_ibm_security_group
from doosra.tasks.other.ibm_tasks import task_attach_subnet_to_public_gateway

LOGGER = logging.getLogger("instance_tasks.py")


@celery.task(name="validate_ibm_volumes", base=IBMBaseTask, bind=True)
def task_validate_ibm_volumes(self, task_id, cloud_id, region, volume):
    """Validate if instance volumes already exists"""
    self.resource_type = 'volumes'
    self.resource_name = volume["name"]
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )
    existing_volume = self.ibm_manager.rias_ops.raw_fetch_ops.get_all_volumes(name=volume["name"])
    if existing_volume:
        raise IBMInvalidRequestError(
            "Volume '{volume}' already exists".format(volume=volume["name"]))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )
    LOGGER.info(
        "IBM volume '{volume}' validated successfully".format(volume=volume["name"]))


@celery.task(name="validate_ibm_instance", base=IBMBaseTask, bind=True)
def task_validate_ibm_instance(self, task_id, cloud_id, region, instance):
    """Validate if instance with same name already exists"""
    self.resource_type = 'instances'
    self.resource_name = instance["name"]
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )
    existing_instance = self.ibm_manager.rias_ops.raw_fetch_ops.get_all_instances(instance["name"])
    if existing_instance:
        raise IBMInvalidRequestError(
            "IBM VSI with name '{}' already configured".format(instance["name"]))

    LOGGER.info("IBM VSI with name '{}' validated successfully".format(instance["name"]))
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )


@celery.task(name="validate_ibm_instance_profiles", base=IBMBaseTask, bind=True)
def task_validate_ibm_instance_profile(self, task_id, cloud_id, region, instance_profile):
    """Validate if instance profiles exist"""
    self.resource_type = 'instance_profiles'
    self.resource_name = instance_profile
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=IN_PROGRESS
    )

    existing_instance_profile = self.ibm_manager.rias_ops.raw_fetch_ops.get_all_instance_profiles(
        name=instance_profile)
    if not existing_instance_profile:
        raise IBMInvalidRequestError("IBM Instance Profile '{name}' not found".format(name=instance_profile))

    LOGGER.info("IBM Instance Profile with name '{}' validated successfully".format(instance_profile))
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource_name, resource_type=self.resource_type, stage=VALIDATION,
        status=SUCCESS
    )


@celery.task(name="create_ibm_instances", base=IBMBaseTask, bind=True)
def create_ibm_instance(self, task_id, cloud_id, region, instance_id, instance, ibm_instance_task_id):
    """
    Configure IBM instance on IBM cloud
    :return:
    """
    LOGGER.info("Task create instance for VPC for instance: {instance_id} initiated".format(instance_id=instance_id))
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS, in_focus=True).first()
    if not ibm_instance_task:
        raise TaskFailureError("Instance task for instance id {id} not found in DB".format(id=instance_id))

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=instance_id).first()
    if not ibm_instance:
        raise TaskFailureError("IBM Instance '{id}' not found in DB".format(id=instance_id))

    ibm_instance.status = CREATING
    doosradb.session.commit()

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
        stage=PROVISIONING, status=IN_PROGRESS)

    if instance["image"].get("image_location") in \
            {IBMInstanceTasks.LOCATION_CLASSICAL_VSI, IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE,
             IBMInstanceTasks.LOCATION_COS_VHD, IBMInstanceTasks.LOCATION_COS_VMDK,
             IBMInstanceTasks.LOCATION_COS_QCOW2} or instance.get("data_migration"):
        self.report_path = ".volume_migration"
        self.report_utils.update_reporting(task_id=task_id, resource_name=self.resource.name,
                                           resource_type=self.resource_type,
                                           stage=PROVISIONING, status=IN_PROGRESS, path=self.report_path)

    if instance.get("nas_migration_info") and instance["nas_migration_info"].get("cm_meta_data"):
        ibm_instance.nas_migration_enabled = True
        doosradb.session.commit()
        construct_nas_migration_user_data(instance=instance, region=region, instance_id=instance_id, cloud_id=cloud_id)

    if instance['image'].get('image_location') == IBMInstanceTasks.LOCATION_CLASSICAL_VSI or instance.get(
            "data_migration"):

        only_data_migration = instance["image"].get("image_location") == IBMInstanceTasks.LOCATION_PUBLIC_IMAGE

        if instance.get("data_migration") and instance.get("volume_attachments"):
            # TODO replace deep copy with some other approach
            construct_user_data_script(copy.deepcopy(instance), self.cloud, region=region, instance_id=ibm_instance.id)

        take_snapshot.si(task_id=task_id, cloud_id=cloud_id, region=region, ibm_instance_id=ibm_instance.id,
                         ibm_instance_task_id=ibm_instance_task_id, only_data_migration=only_data_migration).delay()

    elif instance['image'].get('image_location') == IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE:
        export_to_cos.si(task_id=task_id, cloud_id=cloud_id, region=region, ibm_instance_id=ibm_instance.id,
                         ibm_instance_task_id=ibm_instance_task_id).delay()

    elif instance['image'].get('image_location') in \
            [IBMInstanceTasks.LOCATION_COS_VHD, IBMInstanceTasks.LOCATION_COS_VMDK]:
        image_conversion.si(task_id=task_id, cloud_id=cloud_id, region=region, ibm_instance_id=ibm_instance.id,
                            ibm_instance_task_id=ibm_instance_task_id).delay()

    elif instance['image'].get('image_location') == IBMInstanceTasks.LOCATION_COS_QCOW2:
        custom_image_creation.si(
            task_id=task_id, cloud_id=cloud_id, region=region,
            ibm_instance_id=ibm_instance.id, ibm_instance_task_id=ibm_instance_task_id).delay()

    elif instance['image'].get('image_location') == IBMInstanceTasks.LOCATION_CUSTOM_IMAGE:
        vsi_creation.si(task_id=task_id, region=region, cloud_id=cloud_id,
                        ibm_instance_id=instance_id,
                        ibm_instance_task_id=ibm_instance_task_id).delay()

    elif instance['image'].get('image_location') == IBMInstanceTasks.LOCATION_PUBLIC_IMAGE:
        vsi_creation.si(task_id=task_id, region=region, cloud_id=cloud_id,
                        ibm_instance_id=instance_id,
                        ibm_instance_task_id=ibm_instance_task_id).delay()


@celery.task(name="take_snapshot", base=IBMBaseTask, bind=True)
def take_snapshot(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id, only_data_migration=False):
    """
    This method handles taking snapshot for a machine residing in Classic infrastructure
    """
    LOGGER.info("Task take snapshot for instance: {instance_id} initiated".format(instance_id=ibm_instance_id))
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS, task_type=IBMInstanceTasks.TYPE_TAKE_SNAPSHOT,
        in_focus=True).first()
    if not ibm_instance_task:
        raise TaskFailureError(
            "Instance task for instance id {instance_id} not found in DB".format(instance_id=ibm_instance_id))

    if only_data_migration:
        ibm_instance_task.image_location = IBMInstanceTasks.LOCATION_PUBLIC_IMAGE
        doosradb.session.commit()

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance {id} not found in DB ".format(id=ibm_instance_id))

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.snapshot"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS, path=self.report_path)

    ibm_instance.state = INST_CREATING_IMAGE_TEMPLATE
    doosradb.session.commit()

    softlayer_cloud = doosradb.session.query(SoftlayerCloud).filter_by(
        id=ibm_instance_task.classical_account_id).first()
    if not softlayer_cloud:
        ibm_instance_task.status = FAILED
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        raise TaskFailureError("SoftLayer cloud with ID '{id}' not found in db".format(
            id=ibm_instance_task.classical_account_id))

    softlayer_manager = SoftLayerManager(username=softlayer_cloud.username, api_key=softlayer_cloud.api_key)
    fetched_instance = softlayer_manager.fetch_ops.get_instance_by_id(
        instance_id=ibm_instance_task.classical_instance_id)
    ibm_instance_task.classical_image_name = softlayer_manager.fetch_ops.get_classic_image_name(
        image_name=fetched_instance.get("hostname"))
    doosradb.session.commit()

    if not fetched_instance:
        ibm_instance_task.status = FAILED
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        raise IBMInvalidRequestError(
            "Softlayer instance id '{id}' not found in SoftLayer cloud".format(
                id=ibm_instance_task.classical_instance_id))

    LOGGER.info("IBM instance {instance_id}, image template creation starting".format(instance_id=ibm_instance_id))
    captured_image = softlayer_manager.create_ops.capture_image(
        fetched_instance.get("id"), ibm_instance_task.classical_image_name, ibm_instance.is_volume_migration)
    if not captured_image:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        if ibm_instance_task.backup_req_json and ibm_instance_task.backup_req_json.get("original_instance_id"):
            softlayer_manager.create_ops.delete_instance(ibm_instance_task.classical_instance_id)
            ibm_instance_task.classical_instance_id = ibm_instance_task.backup_req_json["original_instance_id"]

        doosradb.session.commit()
        raise IBMInvalidRequestError("IBM instance {id}, image template creation failed".format(id=ibm_instance.id))

    ibm_instance_task.in_focus = False
    ibm_instance_task.image_create_date = captured_image.get('createDate')
    doosradb.session.commit()


@celery.task(name="snapshot_puller", base=IBMBaseTask, bind=True)
def snapshot_puller(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    """
    This method waits for snapshot operation on a give instance
    :return:
    """
    LOGGER.info("Task snapshot puller for instance: {instance_id} running".format(instance_id=ibm_instance_id))
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS, task_type=IBMInstanceTasks.TYPE_TAKE_SNAPSHOT,
        in_focus=False).first()
    if not ibm_instance_task:
        raise TaskFailureError("Instance task for instance id {id} not found in DB".format(id=ibm_instance_id))

    ibm_instance_task.in_focus = True
    doosradb.session.commit()

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance with ID '{id}' not found in DB ".format(id=ibm_instance_id))

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.snapshot"

    softlayer_cloud = doosradb.session.query(SoftlayerCloud).filter_by(
        id=ibm_instance_task.classical_account_id).first()
    if not softlayer_cloud:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("SoftLayer cloud id {id} not found in DB".format(
            id=ibm_instance_task.classical_account_id))

    softlayer_manager = SoftLayerManager(username=softlayer_cloud.username, api_key=softlayer_cloud.api_key)
    if softlayer_manager.fetch_ops.get_instance_by_id(ibm_instance_task.classical_instance_id).get("activeTransaction"):
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        LOGGER.info("IBM instance {id}, image template creation in progress".format(id=ibm_instance_id))
        return

    fetched_image = softlayer_manager.fetch_ops.get_image_by_name(ibm_instance_task.classical_image_name,
                                                                  create_date=ibm_instance_task.image_create_date)
    if not fetched_image:
        if ibm_instance_task.backup_req_json and ibm_instance_task.backup_req_json.get("original_instance_id"):
            softlayer_manager.create_ops.delete_instance(ibm_instance_task.classical_instance_id)
            ibm_instance_task.classical_instance_id = ibm_instance_task.backup_req_json["original_instance_id"]
            doosradb.session.commit()

        LOGGER.error("IBM instance {id}, image template creation failed".format(id=ibm_instance.id))
        raise IBMInvalidRequestError(
            "IBM instance {id}, image template creation failed".format(id=ibm_instance.id))

    ibm_instance_task.classical_image_id = fetched_image.get('id')
    ibm_instance_task.status = IN_PROGRESS
    ibm_instance_task.task_type = IBMInstanceTasks.TYPE_UPLOAD_TO_COS
    ibm_instance_task.in_focus = True
    doosradb.session.commit()

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
        stage=PROVISIONING, status=SUCCESS, path=self.report_path)

    export_to_cos.si(
        task_id=task_id, cloud_id=cloud_id, region=region, ibm_instance_id=ibm_instance.id,
        ibm_instance_task_id=ibm_instance_task.id).delay()


@celery.task(name="export_to_cos", base=IBMBaseTask, bind=True)
def export_to_cos(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    """
    This method exports an image from image template in SL to IBM COS specified bucket
    :return:
    """
    LOGGER.info("Task export to COS for instance: {id} initiated".format(id=ibm_instance_id))
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS, task_type=IBMInstanceTasks.TYPE_UPLOAD_TO_COS,
        in_focus=True).first()
    if not ibm_instance_task:
        raise TaskFailureError("Instance task for instance '{id}' not found in DB".format(id=ibm_instance_id))

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance '{id}' not found in DB ".format(id=ibm_instance_id))

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.cos_export"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
        stage=PROVISIONING, status=IN_PROGRESS, path=self.report_path)

    ibm_instance.state = INST_EXPORT_COS
    doosradb.session.commit()

    softlayer_cloud = doosradb.session.query(SoftlayerCloud).filter_by(
        id=ibm_instance_task.classical_account_id).first()
    if not softlayer_cloud:
        ibm_instance_task.status = FAILED
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        raise TaskFailureError("SoftLayer cloud {id} not found in db".format(id=ibm_instance_task.classical_account_id))

    softlayer_manager = SoftLayerManager(username=softlayer_cloud.username, api_key=softlayer_cloud.api_key)

    # TODO image name number can be choose with random 99 and 20 times try
    fetched_image = softlayer_manager.fetch_ops.get_image_by_id(ibm_instance_task.classical_image_id)
    if not fetched_image:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        if ibm_instance_task.backup_req_json and ibm_instance_task.backup_req_json.get("original_instance_id"):
            softlayer_manager.create_ops.delete_instance(ibm_instance_task.classical_instance_id)
            ibm_instance_task.classical_instance_id = ibm_instance_task.backup_req_json["original_instance_id"]

        doosradb.session.commit()
        raise TaskFailureError("IBM instance {id}, SoftLayer image not found in SoftLayer".format(
            id=ibm_instance_id))

    image_name = fetched_image.get('name')
    ibm_instance_task.classical_image_name = image_name
    ibm_manager = IBMManager(self.cloud, self.region)
    ibm_instance_task.bucket_object = return_cos_object_name(
        ibm_manger=ibm_manager, bucket_name=ibm_instance_task.bucket_name, object_name=image_name) + "-0"
    doosradb.session.commit()

    if ibm_instance.user_data:
        user_data = decrypt_api_key(ibm_instance.user_data)
        user_data = user_data + f'\nINSTANCE_NAME={ibm_instance_task.bucket_object[:-2]}'
        ibm_instance.user_data = encrypt_api_key(user_data)
        doosradb.session.commit()

    LOGGER.info("IBM instance {id}, SoftLayer image {image_id} exporting to cos starting".format
                (id=ibm_instance_id, image_id=ibm_instance_task.classical_image_id))

    cos_url = COS_URI.format(
        region=ibm_instance.region, bucket=ibm_instance_task.bucket_name, image=ibm_instance_task.bucket_object[:-2])
    exported = softlayer_manager.create_ops.export_image(
        fetched_image.get("id"), cos_url, decrypt_api_key(ibm_instance.ibm_cloud.api_key))
    if not exported:
        ibm_instance_task.status = FAILED
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        raise IBMInvalidRequestError(
            "IBM instance {id}, SoftLayer image {image_id} exporting to cos failed".format(
                id=ibm_instance_id, image_id=ibm_instance_task.classical_image_id))

    ibm_instance_task.in_focus = False
    doosradb.session.commit()


@celery.task(name="export_puller", base=IBMBaseTask, bind=True)
def export_puller(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    LOGGER.info("Task export to cos puller for instance: {instance_id} running".format(instance_id=ibm_instance_id))
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS, task_type=IBMInstanceTasks.TYPE_UPLOAD_TO_COS,
        in_focus=False).first()
    if not ibm_instance_task:
        raise TaskFailureError("Instance task for instance id {id} not found in DB".format(id=ibm_instance_id))

    ibm_instance_task.in_focus = True
    doosradb.session.commit()

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance {id} not found in db ".format(id=ibm_instance_id))

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.cos_export"

    softlayer_cloud = doosradb.session.query(SoftlayerCloud).filter_by(
        id=ibm_instance_task.classical_account_id).first()
    if not softlayer_cloud:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("Softlayer cloud id {id} not found in db".format(
            id=ibm_instance_task.classical_account_id))

    softlayer_manager = SoftLayerManager(username=softlayer_cloud.username, api_key=softlayer_cloud.api_key)
    fetched_image = None
    fetched_image_trans = None

    if ibm_instance_task.image_location in {
        IBMInstanceTasks.LOCATION_CLASSICAL_VSI, IBMInstanceTasks.LOCATION_PUBLIC_IMAGE}:
        fetched_image = softlayer_manager.fetch_ops.get_image_by_name(ibm_instance_task.classical_image_name,
                                                                      create_date=ibm_instance_task.image_create_date)
        fetched_image_trans = fetched_image.get("transaction")

    elif ibm_instance_task.image_location == IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE:
        fetched_image = softlayer_manager.fetch_ops.get_image_by_id(ibm_instance_task.classical_image_id)
        fetched_image_trans = fetched_image.get("transaction")

    try:
        ibm_manager = IBMManager(ibm_instance.ibm_cloud, ibm_instance.region)
        exported_image_list = ibm_manager.cos_ops.fetch_ops.get_bucket_objects(
            bucket_name=ibm_instance_task.bucket_name, primary_objects=False)
    except IBMBoto3ReadTimeoutError as ex:
        LOGGER.info(
            "IBM instance '{id}', Read Timeout while checking the status of export to cos, Exception:'{ex}'".format(
                id=ibm_instance.id, ex=ex))
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        return

    volume_count = len(ibm_instance_task.ibm_instance.volume_attachments.filter(
        IBMVolumeAttachment.volume_index.isnot(None)).filter_by(
        type="data").all()) if ibm_instance_task.ibm_instance.is_volume_migration else 1
    cos_expected_list = [ibm_instance_task.bucket_object[:-2] + "-{:d}.vhd".format(i) for i in range(volume_count)]
    if fetched_image_trans or not all(x in exported_image_list for x in cos_expected_list):
        LOGGER.info("IBM instance {id}, SoftLayer image {image_id} exporting to cos in progress".format
                    (id=ibm_instance_id, image_id=ibm_instance_task.classical_image_id))
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        return

    if ibm_instance_task.image_location == IBMInstanceTasks.LOCATION_CLASSICAL_VSI or \
            (ibm_instance_task.image_location == IBMInstanceTasks.LOCATION_PUBLIC_IMAGE and
             ibm_instance.is_volume_migration):
        softlayer_manager.create_ops.delete_image(fetched_image.get('id'))

    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
        stage=PROVISIONING, status=SUCCESS, path=self.report_path)

    if ibm_instance_task.image_location in {
        IBMInstanceTasks.LOCATION_CLASSICAL_VSI, IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE}:
        ibm_instance_task.task_type = IBMInstanceTasks.TYPE_IMAGE_CONVERSION
        ibm_instance_task.status = IN_PROGRESS
        ibm_instance_task.in_focus = True
        doosradb.session.commit()
        image_conversion.si(
            task_id=task_id, cloud_id=cloud_id, region=region, ibm_instance_id=ibm_instance.id,
            ibm_instance_task_id=ibm_instance_task.id).delay()
    else:
        ibm_instance_task.status = IN_PROGRESS
        ibm_instance_task.task_type = IBMInstanceTasks.TYPE_CREATE_VSI
        ibm_instance_task.in_focus = True
        doosradb.session.commit()
        vsi_creation.si(task_id=task_id, region=region, cloud_id=cloud_id,
                        ibm_instance_id=ibm_instance_id,
                        ibm_instance_task_id=ibm_instance_task.id).delay()
        self.report_path = ".volume_migration"
        self.report_utils.update_reporting(
            task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
            stage=PROVISIONING, status=SUCCESS, path=self.report_path)

    if ibm_instance_task.backup_req_json and ibm_instance_task.backup_req_json.get("original_instance_id"):
        softlayer_manager.create_ops.delete_instance(ibm_instance_task.classical_instance_id)
        ibm_instance_task.classical_instance_id = ibm_instance_task.backup_req_json["original_instance_id"]
        doosradb.session.commit()


@celery.task(name="image_conversion", base=IBMBaseTask, bind=True)
def image_conversion(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    """
    This creates a task for image conversion service after getting its size
    :return:
    """
    LOGGER.info("Task image conversion for instance: {instance_id} initiated".format(instance_id=ibm_instance_id))
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS,
        task_type=IBMInstanceTasks.TYPE_IMAGE_CONVERSION, in_focus=True).first()
    if not ibm_instance_task:
        raise TaskFailureError("Instance task for instance id {id} not found in DB".format(id=ibm_instance_id))

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance {id} not found in db ".format(id=ibm_instance_id))

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.qcow2_conversion"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type, stage=PROVISIONING,
        status=IN_PROGRESS, path=self.report_path)

    ibm_instance.state = INST_IMAGE_CONVERTING
    doosradb.session.commit()

    ibm_cloud = ibm_instance.ibm_cloud

    image_format = None
    if ibm_instance_task.image_location in [IBMInstanceTasks.LOCATION_COS_VHD,
                                            IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE,
                                            IBMInstanceTasks.LOCATION_CLASSICAL_VSI]:
        image_format = "vhd"
    elif ibm_instance_task.image_location == IBMInstanceTasks.LOCATION_COS_VMDK:
        image_format = "vmdk"

    if image_format not in ["vhd", "vmdk"]:
        raise TaskFailureError(f"Unsupported image format '{image_format}' for Image Conversion")

    image_size_mb = get_image_size(
        ibm_cloud.id, ibm_instance.region, ibm_instance_task.bucket_name, ibm_instance_task.bucket_object, image_format
    )
    if not image_size_mb:
        ibm_instance_task.status = FAILED
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        raise IBMInvalidRequestError("Could not get size of Image {} COS bucket {} Region {}".format(
            ibm_instance_task.bucket_object, ibm_instance_task.bucket_object, ibm_instance.region))

    image_conversion_task = ImageConversionTask(
        region, ibm_instance_task.bucket_name, ibm_instance_task.bucket_object + f".{image_format}", image_size_mb)
    image_conversion_task.ibm_cloud = ibm_cloud
    doosradb.session.add(image_conversion_task)

    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(id=ibm_instance_task_id).first()
    ibm_instance_task.image_conversion_task_id = image_conversion_task.id
    ibm_instance_task.in_focus = False
    doosradb.session.commit()


@celery.task(name="conversion_puller", base=IBMBaseTask, bind=True)
def conversion_puller(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    """
    This method polls on Image conversion task to make sure conversion is completed
    :return:
    """
    LOGGER.info("Task conversion puller for instance: {id} running".format(id=ibm_instance_id))
    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.qcow2_conversion"
    if not ibm_instance:
        raise TaskFailureError("IBM Instance {id} not found in db ".format(id=ibm_instance_id))

    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS,
        task_type=IBMInstanceTasks.TYPE_IMAGE_CONVERSION, in_focus=False).first()
    if not ibm_instance_task:
        raise TaskFailureError("Instance task for instance id {id} not found in DB".format(id=ibm_instance_id))

    ibm_instance_task.in_focus = True
    doosradb.session.commit()

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance {id} not found in db ".format(id=ibm_instance_id))

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.qcow2_conversion"

    image_conversion_task = ImageConversionTask.query.filter_by(id=ibm_instance_task.image_conversion_task_id).first()
    if not image_conversion_task or image_conversion_task.status == ImageConversionTask.STATUS_FAILED:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise IBMInvalidRequestError(image_conversion_task.message)

    if image_conversion_task.status == ImageConversionTask.STATUS_SUCCESSFUL:
        ibm_instance_task.status = IN_PROGRESS
        ibm_instance_task.task_type = IBMInstanceTasks.TYPE_CREATE_CUSTOM_IMAGE
        ibm_instance_task.in_focus = True
        doosradb.session.commit()

        self.report_utils.update_reporting(
            task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
            stage=PROVISIONING, status=SUCCESS, path=self.report_path)
        # TODO remove vhd file
        custom_image_creation.si(
            task_id=task_id, cloud_id=cloud_id, region=region,
            ibm_instance_id=ibm_instance.id, ibm_instance_task_id=ibm_instance_task.id).delay()
        return

    ibm_instance_task.in_focus = False
    doosradb.session.commit()


@celery.task(name="custom_image_creation", base=IBMBaseTask, bind=True)
def custom_image_creation(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    """
    This task is for spinning a custom image, and polls until it is created. There is no
    separate wait task for this
    :return:
    """
    LOGGER.info(f"Task custom image creation for instance: {ibm_instance_id} initiated")
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS,
        task_type=IBMInstanceTasks.TYPE_CREATE_CUSTOM_IMAGE, in_focus=True).first()

    if not ibm_instance_task:
        raise TaskFailureError(f"Instance task for instance ID {ibm_instance_id} not found in DB")

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError(f"IBM Instance {ibm_instance_id} not found in DB ")

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.custom_image_creation"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
        stage=PROVISIONING, status=IN_PROGRESS, path=self.report_path)

    ibm_manager = IBMManager(self.cloud, self.region)
    ibm_instance_task.custom_image = return_vpc_image_name(
        ibm_manager=ibm_manager, image_name=transform_ibm_name(ibm_instance_task.bucket_object),
        region=region)
    existing_image = ibm_manager.rias_ops.fetch_ops.get_all_images(
        name=ibm_instance_task.custom_image, visibility="private")
    if existing_image:
        ibm_instance_task.status = FAILED
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        raise IBMInvalidRequestError("Image already exists for instance '{}'".format(ibm_instance_task.custom_image))

    ibm_instance.state = INST_CREATING_CUSTOM_IMAGE
    doosradb.session.commit()

    ibm_manager = IBMManager(ibm_instance.ibm_cloud, self.region)
    vpc_image = ibm_manager.rias_ops.fetch_ops.get_all_images(
        name=ibm_instance_task.vpc_image_name or ibm_instance_task.public_image,
        visibility='public')
    if not vpc_image:
        ibm_instance_task.status = FAILED
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance {id} image not found in ibm cloud with name: {img_name}".format(
            id=ibm_instance_id, img_name=ibm_instance_task.vpc_image_name))

    image_template_path = IMAGE_TEMPLATE_PATH.format(
        region=ibm_instance.region,
        bucket=ibm_instance_task.bucket_name,
        image=ibm_instance_task.bucket_object,
    )
    ibm_image = ibm_instance.ibm_image
    ibm_image.operating_system = vpc_image[0].operating_system.make_copy().add_update_db()
    ibm_image.image_template_path = image_template_path
    ibm_image.name = ibm_instance_task.custom_image
    doosradb.session.commit()

    LOGGER.info("Configuring Custom Image: '{}'".format(ibm_instance_task.custom_image))
    LOGGER.info(ibm_image.to_json_body())
    image_client = ImagesClient(cloud_id=cloud_id)
    LOGGER.info("Create IBM Image Json Payload: {}".format(ibm_image.to_json_body()))
    try:
        image_json = image_client.create_image(region=region, image_json=ibm_image.to_json_body())
    except IBMExecuteError as ex:
        LOGGER.info(ex)
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError(f"IBMImage with ID: {ibm_image.id} Failed to Provision with error: {ex.msg}")

    image_obj = IBMImage.from_ibm_json_body(region, image_json)
    ibm_instance.ibm_image.status = image_obj.status
    ibm_instance.ibm_image.cloud_id = cloud_id
    ibm_instance.ibm_image.resource_id = image_obj.resource_id
    ibm_instance_task.in_focus = False
    doosradb.session.commit()

    # TODO when image template is selected and it has volumes attached.
    # TODO secondary volumes templates will also be exported and will not be deleted here.
    # TODO Need to check the volume number from imaget template and then create a list to delete from cos


@celery.task(name="custom_image_creation_puller", base=IBMBaseTask, bind=True)
def custom_image_creation_puller(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(
        id=ibm_instance_task_id, cloud_id=cloud_id, status=IN_PROGRESS,
        task_type=IBMInstanceTasks.TYPE_CREATE_CUSTOM_IMAGE, in_focus=False).first()

    if not ibm_instance_task:
        raise TaskFailureError(f"Instance task for instance ID {ibm_instance_id} not found in DB")
    ibm_instance_task.in_focus = True
    doosradb.session.commit()
    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError(f"IBM Instance {ibm_instance_id} not found in DB ")

    image_client = ImagesClient(cloud_id=cloud_id)

    image_json = image_client.get_image(region=region, image_id=ibm_instance.ibm_image.resource_id)
    if not image_json:
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        LOGGER.info("IBMExecuteError on Custom Image pulling for {}".format(ibm_instance.ibm_image.id))
        return

    ibm_image = IBMImage.from_ibm_json_body(region, image_json)
    if ibm_image.status == FAILED:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        ibm_image.status = FAILED
        ibm_instance.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError(f"IBM Image {ibm_image.resource_id} Failed to provision ")

    elif ibm_image.status != CREATED:
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        LOGGER.info("IBM instance {id}, vpc custom image creation in progress".format(id=ibm_instance_id))
        return

    ibm_instance.ibm_image.status = ibm_image.status
    ibm_instance.ibm_image.size = ibm_image.size
    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ".volume_migration.steps.custom_image_creation"
    self.report_utils.update_reporting(
        task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
        stage=PROVISIONING, status=SUCCESS, path=self.report_path)

    ibm_instance_task.status = IN_PROGRESS
    ibm_instance_task.task_type = IBMInstanceTasks.TYPE_CREATE_VSI
    ibm_instance_task.in_focus = True
    doosradb.session.commit()

    vsi_creation.si(task_id=task_id, region=region, cloud_id=cloud_id,
                    ibm_instance_id=ibm_instance_id,
                    ibm_instance_task_id=ibm_instance_task.id).delay()

    self.report_path = ".volume_migration"
    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_instance.ibm_image)
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.resource.name,
                                       resource_type=self.resource_type,
                                       stage=PROVISIONING, status=SUCCESS, path=self.report_path)

    cos_images = []
    if ibm_instance_task.image_location in [IBMInstanceTasks.LOCATION_COS_VHD, IBMInstanceTasks.LOCATION_COS_VMDK]:
        cos_images = [ibm_instance_task.bucket_object + ".qcow2"]
    elif ibm_instance_task.image_location in [IBMInstanceTasks.LOCATION_CLASSICAL_VSI,
                                              IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE, ]:
        cos_images = [ibm_instance_task.bucket_object + ".vhd", ibm_instance_task.bucket_object + ".qcow2"]
    if cos_images:
        ibm_manager = IBMManager(cloud=ibm_instance.ibm_cloud, region=region)
        ibm_manager.cos_ops.delete_items(bucket_name=ibm_instance_task.bucket_name, items=cos_images)


@celery.task(name="vsi_creation", base=IBMBaseTask, bind=True)
def vsi_creation(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    LOGGER.info("Task ibm vsi creation for instance: {instance_id} initiated".format(instance_id=ibm_instance_id))
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(id=ibm_instance_task_id, cloud_id=cloud_id,
                                                                           status=IN_PROGRESS,
                                                                           task_type=IBMInstanceTasks.TYPE_CREATE_VSI,
                                                                           in_focus=True).first()
    if not ibm_instance_task:
        raise TaskFailureError("Instance task for instance id {id} not found in DB".format(id=ibm_instance_id))

    # TODO `CHECK +1` if instance name similar instance already exist try with +1
    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id, status=CREATING).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance {id} not found in db ".format(id=ibm_instance_id))

    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ""

    ibm_instance.state = INST_INSTANCE_CREATING
    doosradb.session.commit()

    ibm_manager = IBMManager(ibm_instance.ibm_cloud, self.region)
    ibm_instance_profile = ibm_manager.rias_ops.fetch_ops.get_all_instance_profiles(
        name=ibm_instance.ibm_instance_profile.name)
    if ibm_instance_profile:
        ibm_instance_profile[0].add_update_db()

    if ibm_instance_task.image_location == IBMInstanceTasks.LOCATION_PUBLIC_IMAGE:
        image_name = ibm_instance_task.public_image
    else:
        image_name = ibm_instance_task.custom_image

    ibm_image = ibm_manager.rias_ops.fetch_ops.get_all_images(name=image_name)
    if not ibm_image:
        raise IBMInvalidRequestError("IBM Image with name {name} not found".format(name=image_name))

    ibm_instance_copy = ibm_instance.make_copy()
    ibm_instance_copy.ibm_image = ibm_image[0]
    ibm_instance = ibm_instance_copy.add_update_db(ibm_instance.ibm_vpc_network)

    for volume_attachment in ibm_instance.volume_attachments.all():
        volume_profile = ibm_manager.rias_ops.fetch_ops.get_all_volume_profiles(
            name=volume_attachment.volume.volume_profile.name)
        if volume_profile:
            volume_profile[0].add_update_db()
    user_data = ""
    if ibm_instance.is_volume_migration or ibm_instance.nas_migration_enabled or ibm_instance_task.image_location == IBMInstanceTasks.LOCATION_CLASSICAL_VSI:
        user_data = copy.copy(ibm_instance.user_data)
        if ibm_instance.ibm_image.operating_system.family == "Windows Server":
            if ibm_instance.is_volume_migration:
                ibm_instance.user_data = WINDOWS_SVM_SCRIPT.format(
                    WINDOWS_MIG_REQ=decrypt_api_key(ibm_instance.user_data))
            if ibm_instance_task.image_location == IBMInstanceTasks.LOCATION_CLASSICAL_VSI:
                ibm_instance.user_data = f"{ibm_instance.user_data}\n{RESTORE_ADMIN_USER_DATA}" if ibm_instance.user_data else RESTORE_ADMIN_USER_DATA
        elif ibm_instance.is_volume_migration or ibm_instance.nas_migration_enabled:
            temp_user_data = decrypt_api_key(user_data)
            if ibm_instance.nas_migration_enabled:
                temp_user_data = f"{temp_user_data}\n{NAS_MIG_SCRIPT}\n{CONTENT_MIGRATOR_AGENT_DEPLOY_SCRIPT}"
            if ibm_instance.is_volume_migration:
                temp_user_data = f"{temp_user_data}\n{DATA_MIG_SCRIPT}"
            ibm_instance.user_data = temp_user_data

    if ibm_instance_task.fe_json.get("dedicated_host_name"):
        ibm_dedicated_host = \
            ibm_instance.ibm_cloud.dedicated_hosts.filter_by(
                name=ibm_instance_task.fe_json["dedicated_host_name"], region=region
            ).first()
        if not ibm_dedicated_host:
            raise IBMInvalidRequestError(
                f"Dedicated host '{ibm_instance_task.fe_json['dedicated_host_name']}' not found in region {region}"
            )

        if not ibm_dedicated_host.resource_id:
            raise IBMInvalidRequestError(
                f"Dedicated host {ibm_instance_task.fe_json['dedicated_host_name']} does not have resource id"
            )

        ibm_instance.ibm_dedicated_host = ibm_dedicated_host
        doosradb.session.commit()

    elif ibm_instance_task.fe_json.get("dedicated_host_group_name"):
        ibm_dedicated_host_group = \
            ibm_instance.ibm_cloud.dedicated_host_groups.filter_by(
                name=ibm_instance_task.fe_json["dedicated_host_group_name"], region=region
            ).first()
        if not ibm_dedicated_host_group:
            raise IBMInvalidRequestError(
                f"Dedicated host group '{ibm_instance_task.fe_json['dedicated_host_group_name']}' not found in "
                f"region {region}"
            )

        if not ibm_dedicated_host_group.resource_id:
            raise IBMInvalidRequestError(
                f"Dedicated host Group {ibm_instance_task.fe_json['dedicated_host_group_name']} does not have "
                f"resource id"
            )

        ibm_instance.ibm_dedicated_host_group = ibm_dedicated_host_group
        doosradb.session.commit()

    instance_client = InstancesClient(cloud_id=cloud_id)
    LOGGER.info("Create Instance Json Payload: {}".format(ibm_instance.to_json_body()))
    try:
        configured_instance = instance_client.create_instance(region, instance_json=ibm_instance.to_json_body())
    except ClientIBMExecuteError as ex:
        LOGGER.info(ex)
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise

    instance_obj = IBMInstance.from_ibm_json_body(region, configured_instance)
    ibm_instance.resource_id = instance_obj.resource_id
    ibm_instance.user_data = user_data
    ibm_instance.status = CREATING if instance_obj.status == "starting" else instance_obj.status
    ibm_instance_task.instance_id = ibm_instance.id
    ibm_instance_task.status = IN_PROGRESS
    ibm_instance_task.in_focus = False
    doosradb.session.commit()


@celery.task(name="vsi_creation_puller", base=IBMBaseTask, bind=True)
def vsi_creation_puller(self, task_id, cloud_id, region, ibm_instance_id, ibm_instance_task_id):
    LOGGER.info(
        "Task ibm vsi creation puller for instance: {instance_id} initiated".format(instance_id=ibm_instance_id))
    ibm_instance_task = doosradb.session.query(IBMInstanceTasks).filter_by(id=ibm_instance_task_id, cloud_id=cloud_id,
                                                                           status=IN_PROGRESS,
                                                                           task_type=IBMInstanceTasks.TYPE_CREATE_VSI,
                                                                           in_focus=False).first()
    if not ibm_instance_task:
        raise TaskFailureError("Instance task for instance id {id} not found in DB".format(id=ibm_instance_id))

    ibm_instance_task.in_focus = True
    doosradb.session.commit()
    # TODO `CHECK +1` if instance name similar instance already exist try with +1
    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=ibm_instance_id).first()
    if not ibm_instance:
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        doosradb.session.commit()
        raise TaskFailureError("IBM Instance {id} not found in db ".format(id=ibm_instance_id))

    instance_client = InstancesClient(cloud_id)
    instance_json = instance_client.get_instance(region, ibm_instance.resource_id)
    if not instance_json:
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        LOGGER.info("IBMExecuteError on Instance Creation pulling for {}".format(ibm_instance_id))
        return

    instance_obj = IBMInstance.from_ibm_json_body(region, instance_json)
    self.resource = ibm_instance
    self.resource_type = "instances"
    self.report_path = ""
    if instance_obj.status == "ERROR_":
        ibm_instance_task.in_focus = False
        ibm_instance_task.status = FAILED
        ibm_instance.status = FAILED
        doosradb.session.commit()
        message = "IBM Instance with name '{instance}' FAILED to Provision on ibm cloud".format(instance=ibm_instance.name)
        self.report_utils.update_reporting(task_id=task_id, resource_name=self.resource.name,
                                           resource_type=self.resource_type,
                                           stage=PROVISIONING, status=FAILED, message=message, path=self.report_path)
        LOGGER.info(message)
        return
    elif instance_obj.instance_status == "starting":
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        LOGGER.info("IBM instance {id} creation in progress".format(id=ibm_instance_id))
        return

    ibm_instance.status = instance_obj.status
    doosradb.session.commit()
    for network_interface in instance_json["network_interfaces"]:
        network_interface_ = ibm_instance.network_interfaces.filter_by(name=network_interface["name"]).first()
        if network_interface_:
            network_interface_.private_ip = network_interface["primary_ipv4_address"]
            doosradb.session.commit()

    log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, ibm_instance)
    for volume_attachment in ibm_instance.volume_attachments:
        if volume_attachment.is_migration_enabled:
            log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, volume_attachment)
            log_resource_billing(self.cloud.project.user_id, self.cloud.project.id, volume_attachment.volume)
    self.report_utils.update_reporting(task_id=task_id, resource_name=self.resource.name,
                                       resource_type=self.resource_type,
                                       stage=PROVISIONING, status=SUCCESS)
    LOGGER.info("IBM Instance with name '{instance}' created successfully".format(instance=ibm_instance.name))

    network_interfaces = doosradb.session.query(IBMNetworkInterface).filter_by(instance_id=ibm_instance.id).all()
    for network_interface in network_interfaces:
        if network_interface.is_primary:
            network_interface.resource_id = instance_json["primary_network_interface"]["id"]
            doosradb.session.commit()
        ibm_floating_ip = doosradb.session.query(IBMFloatingIP).filter_by(
            network_interface_id=network_interface.id).first()
        if ibm_floating_ip:
            task_create_ibm_floating_ip.delay(task_id=task_id, cloud_id=cloud_id, region=region,
                                              floating_ip_id=ibm_floating_ip.id)

    ibm_instance_task.status = SUCCESS
    ibm_instance_task.in_focus = False
    doosradb.session.commit()

    # TODO after deleting IBM Image will also be deleted and Vsi will have nothing in image section - IBM ROLA
    # TODO lets not delete the custom image so user can use it and create more instances with the same custom image
    # if ibm_instance_task.image_location in {IBMInstanceTasks.LOCATION_CLASSICAL_VSI,
    #                                         IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE,
    #                                         IBMInstanceTasks.LOCATION_COS_VHD,
    #                                         IBMInstanceTasks.LOCATION_COS_QCOW2}:
    #     LOGGER.info(
    #         "Instance id {instance_id}, Custom Image deletion task is initiated for image ID: {image_id}".format(
    #             instance_id=ibm_instance.id, image_id=ibm_instance.image_id))
    #     img_task = IBMTask(
    #         task_id=None, type_="IMAGE", region=region, action="DELETE",
    #         cloud_id=cloud_id, resource_id=ibm_instance.ibm_image.id)
    #
    #     doosradb.session.add(img_task)
    #     ibm_instance.ibm_image.status = DELETING
    #     doosradb.session.commit()
    #
    #     task_delete_image.si(task_id=img_task.id, cloud_id=cloud_id,
    #                          region=region, image_id=ibm_instance.ibm_image.id).delay()


@celery.task(name="complete_instance_tasks")
def complete_instance_tasks():
    """Fetch all clouds and Run Incomplete Tasks for Instances"""
    LOGGER.info("Starting task 'complete_instance_tasks', Loading all Clouds")
    clouds = doosradb.session.query(IBMCloud).filter_by(status=VALID).all()
    task_mapping_dict = {IBMInstanceTasks.TYPE_TAKE_SNAPSHOT: snapshot_puller,
                         IBMInstanceTasks.TYPE_UPLOAD_TO_COS: export_puller,
                         IBMInstanceTasks.TYPE_IMAGE_CONVERSION: conversion_puller,
                         IBMInstanceTasks.TYPE_CREATE_CUSTOM_IMAGE: custom_image_creation_puller,
                         IBMInstanceTasks.TYPE_CREATE_VSI: vsi_creation_puller}

    for cloud in clouds:
        for ins_incomplete_tasks in doosradb.session.query(IBMInstanceTasks).filter_by(
                status=IN_PROGRESS, in_focus=False, cloud_id=cloud.id).all():
            if ins_incomplete_tasks.backup_req_json and ins_incomplete_tasks.backup_req_json.get("backup"):
                create_backup.si(ibm_instance_task_id=ins_incomplete_tasks.id,
                                 task_id=ins_incomplete_tasks.base_task_id,
                                 region=ins_incomplete_tasks.ibm_instance.region, cloud_id=cloud.id).delay()
            else:
                try:
                    task_mapping_dict[ins_incomplete_tasks.task_type].si(
                        task_id=ins_incomplete_tasks.base_task_id, cloud_id=cloud.id,
                        region=ins_incomplete_tasks.ibm_instance.region,
                        ibm_instance_id=ins_incomplete_tasks.ibm_instance.id,
                        ibm_instance_task_id=ins_incomplete_tasks.id).delay()
                except AttributeError:
                    LOGGER.info("Task has extra task type {status}".format(status=ins_incomplete_tasks.task_type))


@celery.task(name="task_delete_ibm_instance", base=IBMBaseTask, bind=True)
def task_delete_ibm_instance(self, task_id, region, cloud_id, instance_id):
    """
    This request deletes an instance and its resources
    such as network interface and floating ip
    @return:
    """
    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=instance_id).first()
    if not ibm_instance:
        return

    self.resource = ibm_instance
    ibm_instance.status = DELETING
    doosradb.session.commit()

    fetched_instance = self.ibm_manager.rias_ops.fetch_ops.get_all_instances(
        ibm_instance.name, vpc_name=ibm_instance.ibm_vpc_network.name,
        required_relations=False
    )

    if fetched_instance:
        self.ibm_manager.rias_ops.delete_instance(fetched_instance[0])

    ibm_instance.status = DELETED
    doosradb.session.delete(ibm_instance)
    doosradb.session.commit()
    LOGGER.info("IBM instance '{name}' deleted successfully on IBM Cloud".format(name=ibm_instance.name))


@celery.task(name="task_delete_ibm_instance_workflow", base=IBMBaseTask, bind=True)
def task_delete_ibm_instance_workflow(self, task_id, region, cloud_id, instance_id):
    """
    This request deletes instance and its floating ip
    @return:
    """

    workflow_steps, floating_ip_tasks_list = list(), list(),

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=instance_id).first()
    if not ibm_instance:
        return

    for network_interface in ibm_instance.network_interfaces.all():
        if network_interface.floating_ip:
            floating_ip_tasks_list.append(task_delete_ibm_floating_ip.si(
                task_id=task_id, cloud_id=cloud_id,
                region=region, floating_ip_id=network_interface.floating_ip.id))

    if floating_ip_tasks_list and len(floating_ip_tasks_list) == 1:
        workflow_steps.extend(floating_ip_tasks_list)
    elif floating_ip_tasks_list:
        workflow_steps.append(
            chord(group(floating_ip_tasks_list), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Floating IP's Tasks Chord Finisher")))

    workflow_steps.append(task_delete_ibm_instance.si(
        task_id=task_id, cloud_id=cloud_id, region=region, instance_id=ibm_instance.id))

    workflow_steps.append(update_ibm_task.si(task_id=task_id))
    chain(workflow_steps).delay()


@celery.task(name="delete_temp_resource_from_instance", bind=True)
def delete_migration_resources(self, secondary_volume_task_id):
    """Delete all resources Created for volume migration """

    secondary_volume_task = doosradb.session.query(SecondaryVolumeMigrationTask).filter_by(
        id=secondary_volume_task_id).first()
    if not secondary_volume_task:
        LOGGER.info("No secondary_volume_migration_task associated with ID: {}".format(secondary_volume_task_id))
        return
    LOGGER.info("Deleting Secondary Volumes for COS Bucket for instance id {instance_id}".format(
        instance_id=secondary_volume_task.instance_id))
    instance = doosradb.session.query(IBMInstance).filter_by(id=secondary_volume_task.instance_id).first()
    if not instance:
        LOGGER.info("No IBMInstance associated with ID: {}".format(secondary_volume_task.instance_id))
        return

    ibm_manager = IBMManager(instance.ibm_cloud, instance.region)
    volume_attachements = instance.volume_attachments.filter_by(type='data').all()
    instance_task = instance.instance_tasks.first()
    if instance_task:
        # if instance.get("delete_cos_images"):
        ibm_manager.cos_ops.delete_items(bucket_name=instance_task.bucket_name, items=[
            instance_task.bucket_object[:-2] + "-{v_index}.vhd".format(v_index=v_index) for v_index in
            range(len(volume_attachements) + 3)])

    # if instance.get("delete_security_group"):
    primary_network_interface = secondary_volume_task.ibm_instance.network_interfaces.filter_by(is_primary=True).first()
    if primary_network_interface:
        security_group = primary_network_interface.security_groups.filter_by(name="vpc-plus-allow-all").first()
        if security_group:
            try:
                if not instance.nas_migration_enabled :
                    ibm_manager.rias_ops.detach_network_interface_from_security_group(ibm_security_group=security_group,
                                                                                      network_interface=primary_network_interface)
                # ibm_manager.rias_ops.delete_security_group(security_group)
            except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
                LOGGER.info("Error Detaching security group.. ")
                LOGGER.info(ex)
        else:
            LOGGER.info("No vpc_allow_all_sg in interface with ID: {}".format(primary_network_interface.id))
    else:
        LOGGER.info("No primary interface attached with instance: {}".format(secondary_volume_task.ibm_instance.id))


@celery.task(name="task_create_ibm_instance_workflow", base=IBMBaseTask, bind=True)
def task_create_ibm_instance_workflow(self, task_id, region, cloud_id, instance_data, instance_id):
    LOGGER.info("Task ibm vsi workflow for instance: {instance_id} initiated".format(instance_id=instance_id))

    workflow_steps, validation_tasks, floating_ip_tasks_list, ssh_keys_tasks_list = list(), list(), list(), list()
    provisioning_dict, validation_dict = {}, {}
    validation_status, provisioning_status, report_status = PENDING, PENDING, PENDING
    instance_report_list, instance_profile_report_list, image_report_list = list(), list(), list()
    floating_ip_report_dict, volume_report_list = list(), list()

    ibm_instance = doosradb.session.query(IBMInstance).filter_by(id=instance_id).first()
    if not ibm_instance:
        return

    ibm_vpc_network = ibm_instance.ibm_vpc_network
    if not ibm_vpc_network:
        return

    ibm_vpc_report = ibm_vpc_network.to_report_json()
    provisioning_dict.update(ibm_vpc_report)
    validation_dict.update(ibm_vpc_report)

    windows_ = [instance_data.get("original_operating_system_name"), instance_data.get("original_image"),
                instance_data["image"].get("vpc_image_name"), instance_data["image"].get("public_image")]
    windows = [wind.upper() for wind in windows_ if wind]

    windows_backup = "WINDOWS" in windows[0] if windows else False

    ibm_instance_report = ibm_instance.to_report_json()
    migration_report = self.report_utils.get_migration_steps(
        image_location=instance_data["image"].get("image_location"),
        data_migration=instance_data.get("data_migration"),
        windows_backup=windows_backup
    )
    if migration_report:
        ibm_instance_report.update(migration_report)

    instance_report_list.append(ibm_instance_report)
    instance_profile_report_list.append(ibm_instance.ibm_instance_profile.to_report_json())

    # TODO validation for same profile is happening multiple times, need to fix it like done in reporting
    validation_tasks.append(task_validate_ibm_instance_profile.si(
        task_id=task_id, cloud_id=cloud_id, region=region, instance_profile=instance_data["instance_profile"]))

    for ssh_key in instance_data.get("ssh_keys", []):
        ibm_ssh_key = self.cloud.ssh_keys.filter(
            IBMSshKey.public_key == ssh_key, IBMSshKey.region == self.region).first()
        ibm_instance.ssh_keys.append(ibm_ssh_key)
        doosradb.session.commit()

    for volume_attachment in instance_data.get("volume_attachments", list()):
        # TODO When frontend fix the payload we also need to fix it.
        ibm_volume_attachment = IBMVolumeAttachment(
            name=volume_attachment["name"],
            type_=volume_attachment.get("type") or "data",
            is_delete=volume_attachment.get("auto_delete"),
            is_migration_enabled=volume_attachment.get("is_migration_enabled") or False,
            volume_index=volume_attachment.get("volume_index")
        )
        ibm_volume = IBMVolume(
            name=volume_attachment["name"],
            capacity=volume_attachment.get("capacity") or 100,
            zone=instance_data["zone"],
            region=region,
            iops=volume_attachment.get("iops") or 3000,
            encryption=instance_data.get("encryption") or "provider_managed",
            cloud_id=self.cloud.id,
            original_capacity=volume_attachment["volume"].get("original_capacity") if volume_attachment.get(
                "volume") else None
        )

        volume_profile = IBMVolumeProfile(
            name=volume_attachment.get("volume_profile_name") or volume_attachment.get(
                "volume_profile_type") or "general-purpose",
            region=self.region,
            cloud_id=cloud_id)
        volume_profile = volume_profile.get_existing_from_db() or volume_profile
        ibm_volume.volume_profile = volume_profile
        ibm_volume_attachment.volume = ibm_volume
        ibm_instance.volume_attachments.append(ibm_volume_attachment)
        doosradb.session.commit()
        volume_report_list.append(ibm_volume.to_report_json())

        # TODO we should remove validation and add +1 in the volume
        validation_tasks.append(
            task_validate_ibm_volumes.si(
                task_id=task_id, cloud_id=cloud_id, region=region, volume=volume_attachment))

    ibm_volume = IBMVolume(
        name=get_volume_name(instance_data["name"]),
        capacity=100,
        zone=instance_data["zone"],
        region=region,
        iops=3000,
        encryption="provider_managed",
        cloud_id=self.cloud.id,
    )
    ibm_boot_volume_attachment = IBMVolumeAttachment(
        name=get_volume_name(instance_data["name"]),
        type_="boot",
        is_delete=True,
    )
    volume_profile = IBMVolumeProfile(name="general-purpose", region=region, cloud_id=cloud_id)
    volume_profile = volume_profile.get_existing_from_db() or volume_profile
    ibm_volume.volume_profile = volume_profile
    ibm_boot_volume_attachment.volume = ibm_volume
    ibm_instance.volume_attachments.append(ibm_boot_volume_attachment)
    doosradb.session.commit()

    if instance_data["image"].get("public_image") or instance_data["image"].get("vpc_image_name"):
        image_name = (
            instance_data["image"]["public_image"]
            if instance_data["image"].get("public_image")
            else None or instance_data["image"].get("vpc_image_name")
            if instance_data["image"].get("vpc_image_name")
            else None
        )
        # TODO validation for same image is happening multiple times, need to fix it like done in reporting
        validation_tasks.append(
            task_validate_ibm_images.si(
                task_id=task_id,
                cloud_id=cloud_id,
                region=region,
                image_name=image_name
            )
        )
        image_report_list.append({
            "name": '{image_name}'.format(image_name=image_name), "status": PENDING,
            "message": ""
        })

    # Handle Creation/Attachment of Public Gateway(subnet) and Security Group(interface) for Secondary Volume Migration
    allow_all_security_group = None
    if instance_data.get("data_migration"):
        if not instance_data.get("allow_all_security_group_id"):
            allow_all_security_group = IBMSecurityGroup(instance_data.get("allow_all_security_group_id"),
                                                        instance_data.get("region"), cloud_id=cloud_id,
                                                        vpc_id=ibm_vpc_network.id)
            for direction in ["inbound", "outbound"]:
                rule = IBMSecurityGroupRule(direction, protocol="all", rule_type="any")
                allow_all_security_group.rules.append(rule)
            allow_all_security_group.ibm_resource_group = ibm_vpc_network.ibm_resource_group
            allow_all_security_group.ibm_vpc_network = ibm_vpc_network
            doosradb.session.commit()
            task_add_ibm_security_group.delay(
                task_id=task_id, cloud_id=cloud_id, region=region, security_group_id=allow_all_security_group.id)
        else:
            allow_all_security_group = doosradb.session.query(IBMSecurityGroup).filter_by(
                id=instance_data.get("allow_all_security_group_id")).first()

    if instance_data.get('network_interfaces'):
        for index, network_interface in enumerate(instance_data.get("network_interfaces", [])):
            ibm_network_interface = IBMNetworkInterface(
                name=network_interface["name"],
                is_primary=network_interface["is_primary"])

            if instance_data.get("data_migration"):
                task_attach_subnet_to_public_gateway.delay(network_interface["subnet_id"])

            ibm_subnet = ibm_vpc_network.subnets.filter(
                IBMSubnet.id == network_interface["subnet_id"]).first()
            ibm_network_interface.ibm_subnet = ibm_subnet
            ibm_network_interface.instance_id = instance_id
            doosradb.session.commit()

            for security_group in network_interface.get("security_groups", []):
                allow_all_sec_grp_exists = allow_all_security_group in ibm_network_interface.security_groups
                if allow_all_security_group and not allow_all_sec_grp_exists:
                    ibm_network_interface.security_groups.append(allow_all_security_group)

                ibm_security_group = ibm_vpc_network.security_groups.filter(
                    IBMSecurityGroup.id == security_group).first()

                ibm_security_group_exists = ibm_security_group in ibm_network_interface.security_groups

                if ibm_security_group and not ibm_security_group_exists:
                    ibm_network_interface.security_groups.append(ibm_security_group)

                doosradb.session.commit()

            if network_interface.get("reserve_floating_ip"):
                floating_ip = instance_data["name"][13:] if len(instance_data["name"]) > 50 else instance_data["name"]
                ibm_floating_ip = IBMFloatingIP(
                    name=FLOATING_IP_NAME.format(floating_ip, index),
                    region=region,
                    zone=ibm_instance.zone,
                    cloud_id=cloud_id,
                )
                ibm_network_interface.floating_ip = ibm_floating_ip
                doosradb.session.commit()
                floating_ip_report_dict.append(ibm_floating_ip.to_report_json())

            ibm_instance.network_interfaces.append(ibm_network_interface)
            doosradb.session.commit()

    if instance_report_list:
        INSTANCE_TEMPLATE[INSTANCE_KEY][RESOURCES_KEY] = instance_report_list
        provisioning_dict.update(INSTANCE_TEMPLATE)

    if floating_ip_report_dict:
        FLOATING_IP_TEMPLATE[FLOATING_IP_KEY][RESOURCES_KEY] = floating_ip_report_dict
        provisioning_dict.update(FLOATING_IP_TEMPLATE)

    if instance_profile_report_list:
        INSTANCE_PROFILE_TEMPLATE[INSTANCE_PROFILE_KEY][RESOURCES_KEY] = instance_profile_report_list
        validation_dict.update(INSTANCE_PROFILE_TEMPLATE)

    if image_report_list:
        IMAGE_TEMPLATE[IMAGE_KEY][RESOURCES_KEY] = image_report_list
        validation_dict.update(IMAGE_TEMPLATE)

    if volume_report_list:
        VOLUME_TEMPLATE[VOLUME_KEY][RESOURCES_KEY] = volume_report_list
        validation_dict.update(VOLUME_TEMPLATE)

    if validation_tasks and len(validation_tasks) == 1:
        workflow_steps.extend(validation_tasks)
    elif validation_tasks:
        workflow_steps.append(
            chord(group(validation_tasks), update_group_tasks.si(
                task_id=task_id, cloud_id=cloud_id, region=region, message="Validation Tasks Chord Finisher")))

    ibm_instance_task_id = instance_task_insert(task_id=task_id, cloud_id=cloud_id, instance_id=ibm_instance.id,
                                                instance=instance_data)

    if windows_backup and instance_data['image'].get(
            'image_location') == IBMInstanceTasks.LOCATION_CLASSICAL_VSI:
        ibm_instance_task = IBMInstanceTasks.query.get(ibm_instance_task_id)
        if not ibm_instance_task:
            raise TaskFailureError(f"IBMInstanceTasks {ibm_instance_task_id} deleted from db...")
        ibm_instance_task.backup_req_json = {"instance_data": instance_data, "step": 1,
                                             "ibm_instance_id": ibm_instance.id, "backup": True}
        doosradb.session.commit()
        workflow_steps.append(
            create_backup.si(ibm_instance_task_id=ibm_instance_task_id, task_id=task_id, cloud_id=cloud_id,
                             region=region, in_focus=True))
    else:
        workflow_steps.append(
            create_ibm_instance.si(task_id=task_id, cloud_id=cloud_id, region=region, instance_id=ibm_instance.id,
                                   instance=instance_data, ibm_instance_task_id=ibm_instance_task_id))
    workflow_steps.append(update_ibm_task.si(task_id=task_id))

    if ibm_vpc_network.status == CREATED and len(validation_dict) == 1:
        validation_status = SUCCESS

    if ibm_vpc_network.status == CREATED and len(provisioning_dict) == 1:
        provisioning_status = SUCCESS
        LOGGER.error("Nothing has been added for provisoning")

    if provisioning_status == SUCCESS and validation_status == SUCCESS:
        report_status = SUCCESS

    provisioning = {"status": provisioning_status, "message": "", "steps": provisioning_dict}
    validation = {"status": validation_status, "message": "", "steps": validation_dict}
    report = {"status": report_status, "message": "", "steps": {"provisioning": provisioning, "validation": validation}}

    task = doosradb.session.query(IBMTask).filter(IBMTask.id == task_id).first()
    task.report = report
    doosradb.session.commit()
    LOGGER.info("Initial report for taskID: '{task_id}' created successfully \n'{report}'".format(task_id=task_id,
                                                                                                  report=report))

    chain(workflow_steps).delay()


def instance_task_insert(task_id, cloud_id, instance_id, instance):
    LOGGER.info("Task create instance for instance: {instance_id} inserted into db".format(instance_id=instance_id))
    task_type_mapper = {IBMInstanceTasks.LOCATION_CLASSICAL_VSI: IBMInstanceTasks.TYPE_TAKE_SNAPSHOT,
                        IBMInstanceTasks.LOCATION_CLASSICAL_IMAGE: IBMInstanceTasks.TYPE_UPLOAD_TO_COS,
                        IBMInstanceTasks.LOCATION_COS_VHD: IBMInstanceTasks.TYPE_IMAGE_CONVERSION,
                        IBMInstanceTasks.LOCATION_COS_VMDK: IBMInstanceTasks.TYPE_IMAGE_CONVERSION,
                        IBMInstanceTasks.LOCATION_COS_QCOW2: IBMInstanceTasks.TYPE_CREATE_CUSTOM_IMAGE,
                        IBMInstanceTasks.LOCATION_CUSTOM_IMAGE: IBMInstanceTasks.TYPE_CREATE_VSI,
                        IBMInstanceTasks.LOCATION_PUBLIC_IMAGE: IBMInstanceTasks.TYPE_CREATE_VSI}

    image_type = instance["extras"].get("image_type") if instance.get("extras") else None

    ibm_instance_task = IBMInstanceTasks(base_task_id=task_id,
                                         cloud_id=cloud_id,
                                         instance_id=instance_id,
                                         status=IN_PROGRESS,
                                         task_type=task_type_mapper[instance['image'].get('image_location')],
                                         image_location=instance['image'].get('image_location'),
                                         in_focus=True,
                                         classical_account_id=instance['image'].get('classical_account_id'),
                                         classical_image_id=instance['image'].get('classical_image_id'),
                                         classical_instance_id=instance['image'].get('classical_instance_id'),
                                         bucket_name=instance['image'].get('bucket_name'),
                                         bucket_object=instance['image'].get('bucket_object'),
                                         custom_image=instance['image'].get('custom_image'),
                                         public_image=instance['image'].get('public_image'),
                                         vpc_image_name=instance['image'].get('vpc_image_name'),
                                         image_type=image_type,
                                         fe_json=instance)
    doosradb.session.add(ibm_instance_task)
    if instance.get("data_migration"):
        ibm_instance_task.task_type = IBMInstanceTasks.TYPE_TAKE_SNAPSHOT
    doosradb.session.commit()
    return ibm_instance_task.id


@celery.task(name="delete_windows_cos_vhds")
def delete_windows_resources(instance_id):
    """Delete all cos resources Created for volume migration of the specific instance"""
    instance = doosradb.session.query(IBMInstance).filter_by(id=instance_id).first()
    if not instance:
        LOGGER.info("No IBMInstance associated with ID: {}".format(instance_id))
        return

    ibm_manager = IBMManager(instance.ibm_cloud, instance.region)
    instance_task = instance.instance_tasks.first()
    if instance_task:
        items = [instance_task.bucket_object[:-2] + "-{v_index}.vhd".format(v_index=v_index) for v_index in range(5)]
        ibm_manager.cos_ops.delete_items(bucket_name=instance_task.bucket_name, items=items)

    primary_network_interface = instance.network_interfaces.filter_by(is_primary=True).first()
    if primary_network_interface:
        security_group = primary_network_interface.security_groups.filter_by(name="vpc-plus-allow-all").first()
        if security_group:
            try:
                ibm_manager.rias_ops.detach_network_interface_from_security_group(
                    ibm_security_group=security_group,
                    network_interface=primary_network_interface)
            except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
                LOGGER.info("Error Detaching security group.. ")
                LOGGER.info(ex)
        else:
            LOGGER.info("No vpc_allow_all_sg in interface with ID: {}".format(primary_network_interface.id))
    else:
        LOGGER.info("No primary interface attached with instance: {}".format(instance.id))


@celery.task(name="task_create_backup", base=IBMBaseTask, bind=True)
def create_backup(self, task_id, region, cloud_id, ibm_instance_task_id, in_focus=False):
    LOGGER.info(f"Classic Windows Backup task initiated IBMInstanceTask ID: {ibm_instance_task_id}")
    ibm_instance_task = IBMInstanceTasks.query.filter_by(id=ibm_instance_task_id, in_focus=in_focus,
                                                         status=IN_PROGRESS).first()
    if not ibm_instance_task:
        LOGGER.info(f"IBMInstanceTasks id: {ibm_instance_task_id} not failed")
        TaskFailureError(msg="Failed to take backup server for windows")
    ibm_instance_task.in_focus = True
    doosradb.session.commit()
    if in_focus and ibm_instance_task.backup_req_json:
        ibm_instance = IBMInstance.query.get(ibm_instance_task.backup_req_json["ibm_instance_id"])
        if ibm_instance:
            self.resource = ibm_instance
            self.resource_type = "instances"
            self.report_utils.update_reporting(
                task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                stage=PROVISIONING, status=IN_PROGRESS)

            self.report_path = ".volume_migration"
            self.report_utils.update_reporting(
                task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                stage=PROVISIONING, status=IN_PROGRESS, path=self.report_path)

            ibm_instance.status = CREATING
            doosradb.session.commit()

    softlayer_cloud = SoftlayerCloud.query.get(ibm_instance_task.classical_account_id)
    softlayer_manager = SoftLayerManager(username=softlayer_cloud.username,
                                         api_key=softlayer_cloud.api_key)
    backup_json = copy.copy(ibm_instance_task.backup_req_json)
    if backup_json.get("step") == 1:
        LOGGER.info(f"Softlayer Windows VSI for {ibm_instance_task.classical_instance_id} Backup snapshot started")
        image_captured = softlayer_manager.create_ops.capture_image(instance_id=ibm_instance_task.classical_instance_id,
                                                                    image_name=backup_json["instance_data"]["name"],
                                                                    additional_disks=backup_json["instance_data"].get(
                                                                        "data_migration"))
        backup_json["step"] = 2
        backup_json["backup_image_creation_date"] = image_captured["createDate"]
        ibm_instance_task.backup_req_json = backup_json
        ibm_instance_task.in_focus = False
        doosradb.session.commit()
        ibm_instance = IBMInstance.query.get(ibm_instance_task.backup_req_json["ibm_instance_id"])
        if ibm_instance:
            self.resource = ibm_instance
            self.resource_type = "instances"
            self.report_path = ".volume_migration.steps.windows_backup"
            self.report_utils.update_reporting(
                task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                stage=PROVISIONING, status=IN_PROGRESS, path=self.report_path)
        return
    elif backup_json.get("step") == 2:
        old_vsi = softlayer_manager.fetch_ops.get_instance_by_id(ibm_instance_task.classical_instance_id)
        if old_vsi.get("activeTransaction"):
            LOGGER.info(f"Softlayer Instance Snapshot is in progress for ID: {ibm_instance_task.classical_instance_id}")
            ibm_instance_task.in_focus = False
            doosradb.session.commit()
            return
        else:
            backup_image_json = softlayer_manager.fetch_ops.get_image_by_name(
                image_name=backup_json["instance_data"]["name"], create_date=backup_json["backup_image_creation_date"])
            if not (old_vsi and backup_image_json):
                TaskFailureError(
                    msg=f"Classical Instance {ibm_instance_task.classical_instance_id} or Classical Backup Image"
                        f"{backup_json['instance_data']['name']} not found in IBM Softlayer")
            try:
                new_vsi_dict = {
                    "cpus": old_vsi['maxCpu'],
                    "memory": old_vsi['maxMemory'],
                    "hourly": old_vsi['hourlyBillingFlag'],
                    "hostname": "v" + old_vsi['hostname'][-7:] + "backup",
                    "domain": old_vsi['domain'],
                    "datacenter": old_vsi["datacenter"]["name"],
                    "image_id": backup_image_json["globalIdentifier"],
                    "local_disk": False,
                    "userdata": IBM_GEN2_WINDOWS_REQ_STRING,
                    "dedicated": old_vsi.get('dedicatedAccountHostOnlyFlag'),
                    "private": old_vsi.get('privateNetworkOnlyFlag'),
                    "tags": "DO-NOT-DELETE, TEMPORARY, WINDOWS-BACKUP",
                    "ssh_keys": [sshkey.id for sshkey in old_vsi['sshKeys']] if old_vsi.get('sshKeys') else []
                }
            except KeyError as ex:
                TaskFailureError(
                    msg=f"{ex.__str__()} Missing in IBM response for instance {ibm_instance_task.classical_instance_id}")
            backup_vsi = softlayer_manager.create_ops.create_instance(new_vsi_dict)
            backup_json["backup_instance_id"] = backup_vsi["id"]
            backup_json["backup_image_id"] = backup_image_json["id"]
            backup_json["step"] = 3
            ibm_instance_task.in_focus = False
            ibm_instance_task.backup_req_json = backup_json
            doosradb.session.commit()
            LOGGER.info(f"Softlayer Windows Backup Instance created with ID: {backup_vsi['id']}")
    elif backup_json.get("step") == 3:
        if not softlayer_manager.fetch_ops.wait_instance_for_ready(backup_json["backup_instance_id"], limit=2):
            ibm_instance_task.in_focus = False
            doosradb.session.commit()
            LOGGER.info(f"Softlayer Instance with ID {backup_json['backup_instance_id']} is in progress..")
            return
        else:
            ip = softlayer_manager.fetch_ops.get_instance_by_id(backup_json["backup_instance_id"])["primaryIpAddress"]
            res = os.system(f"ping -w5 {ip}")
            LOGGER.info(res)
            if res == 0:
                ibm_instance_task.in_focus = False
                doosradb.session.commit()
                return
            else:
                LOGGER.info(f"{ibm_instance_task.instance_id} is getting ready for sysprep to be migrated ... !")
                if not backup_json.get("wait_count"):
                    backup_json["wait_count"] = 1
                    ibm_instance_task.backup_req_json = backup_json
                    ibm_instance_task.in_focus = False
                    doosradb.session.commit()
                    return
                else:
                    if backup_json["wait_count"] < 15:
                        backup_json["wait_count"] += 1
                        ibm_instance_task.backup_req_json = backup_json
                        ibm_instance_task.in_focus = False
                        doosradb.session.commit()
                        return

        instance_id = ibm_instance_task.classical_instance_id
        ibm_instance_task.classical_instance_id = backup_json["backup_instance_id"]
        ibm_instance_id = backup_json["ibm_instance_id"]
        instance_data = backup_json["instance_data"]
        backup_json = {"original_instance_id": instance_id, "backup_image_id": backup_json["backup_image_id"]}

        ibm_instance_task.backup_req_json = backup_json
        ibm_instance_task.in_focus = True
        doosradb.session.commit()
        softlayer_manager.create_ops.delete_image(backup_json["backup_image_id"])
        LOGGER.info(softlayer_manager.fetch_ops.get_instance_by_id(ibm_instance_task.classical_instance_id))
        ibm_instance = IBMInstance.query.get(ibm_instance_id)
        if ibm_instance:
            self.resource = ibm_instance
            self.resource_type = "instances"
            self.report_path = ".volume_migration.steps.windows_backup"
            self.report_utils.update_reporting(
                task_id=task_id, resource_name=self.resource.name, resource_type=self.resource_type,
                stage=PROVISIONING, status=SUCCESS, path=self.report_path)
        LOGGER.info(f"Windows Machine Backup Machine for ID: {ibm_instance_id} Created Successfully ...!")
        create_ibm_instance.si(task_id=task_id, cloud_id=cloud_id, region=region,
                               instance_id=ibm_instance_id,
                               instance=instance_data, ibm_instance_task_id=ibm_instance_task_id).delay()
