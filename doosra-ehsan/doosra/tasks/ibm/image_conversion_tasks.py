"""
This file contains background and scheduled tasks related to Image Migration
"""

import ibm_boto3
from flask import current_app
from ibm_botocore.client import Config
from jsonschema import validate, ValidationError

from doosra import db as doosradb
from doosra.common.image_conversion.ic_softlayer_manager import ICSoftlayerManager
from doosra.common.image_conversion.ic_softlayer_manager.exceptions import SLAuthException, \
    SLResourceNotFoundException, UnexpectedSLError
from doosra.common.image_conversion.ic_softlayer_manager.instance_response_schema import instance_response_schema
from doosra.common.image_conversion.ssh_manager import SSHManager
from doosra.common.utils import decrypt_api_key
from doosra.models import IBMCloud, ImageConversionInstance, ImageConversionTask
from doosra.tasks.celery_app import celery


@celery.task(name="ic_task_distributor", queue="image_conversion_queue")
def image_conversion_task_distributor():
    """
    Scheduled function that handles distribution of tasks to instances (also creates instance entries in database)
    """
    # TODO: find a logic so that if this task is already running, it should not run again

    all_instances = ImageConversionInstance.query.filter_by(status=ImageConversionInstance.STATUS_ACTIVE).all()
    for instance in all_instances:
        if instance.task and instance.task.status not in \
                {ImageConversionTask.STATUS_SUCCESSFUL, ImageConversionTask.STATUS_FAILED}:
            continue

        instance.status = ImageConversionInstance.STATUS_DELETE_PENDING
        instance.task = None
        doosradb.session.commit()

    for created_task in ImageConversionTask.query.filter_by(status=ImageConversionTask.STATUS_CREATED).all():
        if created_task.instance:
            continue

        new_instance = ImageConversionInstance(created_task.region)
        new_instance.task = created_task
        doosradb.session.add(new_instance)
        doosradb.session.commit()


@celery.task(name="ic_instances_overseer", queue="image_conversion_queue")
def image_conversion_instances_overseer():
    """
    Scheduled function that handles creation and deletion of image conversion instances
    """
    # TODO: find a logic so that if this task is already running, it should not run again

    create_pending_state_instances = ImageConversionInstance.query.filter_by(
        status=ImageConversionInstance.STATUS_CREATE_PENDING).all()
    creating_state_instances = ImageConversionInstance.query.filter_by(
        status=ImageConversionInstance.STATUS_CREATING).all()

    for create_pending_state_instance in create_pending_state_instances:
        initiate_pending_instance_creation.delay(create_pending_state_instance.id)

    for creating_state_instance in creating_state_instances:
        get_update_creating_instance.delay(creating_state_instance.id)

    delete_pending_state_instances = ImageConversionInstance.query.filter_by(
        status=ImageConversionInstance.STATUS_DELETE_PENDING).all()
    deleting_state_instances = ImageConversionInstance.query.filter_by(
        status=ImageConversionInstance.STATUS_DELETING).all()

    for delete_pending_state_instance in delete_pending_state_instances:
        initiate_pending_instance_deletion.delay(delete_pending_state_instance.id)

    for deleting_state_instance in deleting_state_instances:
        get_delete_deleting_instance.delay(deleting_state_instance.id)


@celery.task(name="ic_initiate_pending_instance_creation", queue="image_conversion_queue")
def initiate_pending_instance_creation(instance_id):
    """
    Task to initiate instance creation on Softlayer for STATUS_CREATE_PENDING instances
    :param instance_id: <string> ImageConversionInstance ID
    """
    instance = ImageConversionInstance.query.filter_by(id=instance_id).first()
    if not instance or instance.status != ImageConversionInstance.STATUS_CREATE_PENDING or instance.softlayer_id:
        return

    try:
        ic_softlayer_manager = ICSoftlayerManager()
        response = ic_softlayer_manager.create_instance(instance.to_softlayer_json())
    except (SLAuthException, UnexpectedSLError) as ex:
        current_app.logger.info(ex)
        if instance.task:
            instance.task.status = ImageConversionTask.STATUS_FAILED
            instance.task.message = str(ex)
            doosradb.session.commit()
        return

    instance.softlayer_id = response["id"]
    instance.status = ImageConversionInstance.STATUS_CREATING
    doosradb.session.commit()


@celery.task(name="ic_initiate_pending_instance_deletion", queue="image_conversion_queue")
def initiate_pending_instance_deletion(instance_id):
    """
    Task to initiate instance deletion on Softlayer for STATUS_DELETE_PENDING instances
    :param instance_id: <string> ImageConversionInstance ID
    """
    instance = ImageConversionInstance.query.filter_by(id=instance_id).first()
    if not instance or instance.status != ImageConversionInstance.STATUS_DELETE_PENDING or not instance.softlayer_id:
        return

    try:
        ic_softlayer_manager = ICSoftlayerManager()
        ic_softlayer_manager.delete_instance(instance.softlayer_id)
    except (SLAuthException, UnexpectedSLError) as ex:
        current_app.logger.exception(ex)
        return
    except SLResourceNotFoundException:
        doosradb.session.delete(instance)
        doosradb.session.commit()
        return

    instance.status = ImageConversionInstance.STATUS_DELETING
    doosradb.session.commit()


@celery.task(name="ic_get_update_creating_instance", queue="image_conversion_queue")
def get_update_creating_instance(instance_id):
    """
    Task to get a creating instance from Softlayer and update info in db if complete information is acquired
    Also, update the task (if exists) status to STATUS_RUNNING if instance is successfully created and credentials
    are acquired
    :param instance_id: <string> ImageConversionInstance ID
    """
    instance = ImageConversionInstance.query.filter_by(id=instance_id).first()
    if not instance or instance.status != ImageConversionInstance.STATUS_CREATING or not instance.softlayer_id:
        return

    try:
        ic_softlayer_manager = ICSoftlayerManager()
        response = ic_softlayer_manager.get_instance(instance.softlayer_id)
    except (SLAuthException, SLResourceNotFoundException, UnexpectedSLError) as ex:
        current_app.logger.info(ex)
        if instance.task:
            instance.task.status = ImageConversionTask.STATUS_FAILED
            instance.task.message = str(ex)
            doosradb.session.commit()
        return

    try:
        validate(response, instance_response_schema)
    except ValidationError:
        return

    if response["status"]["keyName"] == ImageConversionInstance.STATUS_ACTIVE \
            and response["powerState"]["keyName"] == "RUNNING":
        instance.status = ImageConversionInstance.STATUS_ACTIVE
        instance.update_create_time()

        instance.ip_address = response["primaryIpAddress"]
        instance.username = response["operatingSystem"]["passwords"][0]["username"]
        instance.password = response["operatingSystem"]["passwords"][0]["password"]

        if instance.task:
            instance.task.status = ImageConversionTask.STATUS_RUNNING
        doosradb.session.commit()


@celery.task(name="ic_get_delete_deleting_instance", queue="image_conversion_queue")
def get_delete_deleting_instance(instance_id):
    """
    Task to get a deleting instance from Softlayer. If not found, delete from database
    :param instance_id: <string> ImageConversionInstance ID
    """
    instance = ImageConversionInstance.query.filter_by(id=instance_id).first()
    if not instance or instance.status != ImageConversionInstance.STATUS_DELETING or not instance.softlayer_id:
        return

    try:
        ic_softlayer_manager = ICSoftlayerManager()
        ic_softlayer_manager.get_instance(instance.softlayer_id)
    except (SLAuthException, UnexpectedSLError) as ex:
        current_app.logger.exception(ex)
        return
    except SLResourceNotFoundException:
        doosradb.session.delete(instance)
        doosradb.session.commit()


@celery.task(name="ic_pending_task_executor", queue="image_conversion_queue")
def image_conversion_pending_task_executor():
    """
    Scheduled function that handles execution of pending image conversion tasks
    """
    tasks = ImageConversionTask.query.filter(
        ImageConversionTask.status == ImageConversionTask.STATUS_RUNNING,
        ImageConversionTask.step.in_(
            [
                ImageConversionTask.STEP_PENDING_PROCESS_START,
                ImageConversionTask.STEP_PENDING_CLEANUP,
                ImageConversionTask.STEP_FILES_UPLOADING_RETRY,
                ImageConversionTask.STEP_IMAGE_DOWNLOADING_RETRY
            ]
        )
    ).all()
    for task in tasks:
        if task.step in [
            ImageConversionTask.STEP_PENDING_PROCESS_START, ImageConversionTask.STEP_FILES_UPLOADING_RETRY,
            ImageConversionTask.STEP_IMAGE_DOWNLOADING_RETRY
        ]:
            initiate_image_conversion.delay(task.id)
        elif task.step == ImageConversionTask.STEP_PENDING_CLEANUP:
            initiate_image_conversion_janitor.delay(task.id)


@celery.task(name="initiate_image_conversion", queue="image_conversion_queue")
def initiate_image_conversion(task_id):
    """
    Task to initiate image conversion on the remote instance. Uploads files and then runs image conversion script in
    background
    :param task_id: <string> id of the ImageConversionTask to be initiated
    """
    task = ImageConversionTask.query.filter_by(id=task_id).first()
    if not task or not task.instance:
        return

    ssh_manager = None
    try:
        ssh_manager = SSHManager(task.instance.ip_address, password=task.instance.password)

        if task.step in [
            ImageConversionTask.STEP_PENDING_PROCESS_START, ImageConversionTask.STEP_FILES_UPLOADING_RETRY
        ]:
            task.step = ImageConversionTask.STEP_FILES_UPLOADING
            doosradb.session.commit()

            ssh_manager.write_file("/mnt/image_conversion/", "config.json", task.generate_config_file_contents())
            ssh_manager.send_file_sftp("/doosra-vpc-be/doosra/common/image_conversion/conversion_script.py",
                                       "/mnt/image_conversion/conversion_script.py")

        task.step = ImageConversionTask.STEP_IMAGE_DOWNLOADING
        doosradb.session.commit()
        ssh_manager.run_command(
            "nohup python3 -u /mnt/image_conversion/conversion_script.py {} > /mnt/image_conversion/imc.log &".format(
                task.webhook_url
            )
        )
    except Exception as ex:
        # Catching general exceptions here as Paramiko documentation is a little inconsistent with the exceptions they
        # generate. We can not let this task fail as it can cost us a dangling instance
        if task.retries:
            task.retries -= 1
            if task.step == ImageConversionTask.STEP_FILES_UPLOADING:
                task.step = ImageConversionTask.STEP_FILES_UPLOADING_RETRY
            elif task.step == ImageConversionTask.STEP_IMAGE_DOWNLOADING:
                task.step = ImageConversionTask.STEP_IMAGE_DOWNLOADING_RETRY
            doosradb.session.commit()
            return

        task.status = ImageConversionTask.STATUS_FAILED
        task.message = str(ex)
        doosradb.session.commit()
    finally:
        if ssh_manager:
            ssh_manager.close_ssh_connection()


@celery.task(name="initiate_image_conversion_janitor", queue="image_conversion_queue")
def initiate_image_conversion_janitor(task_id):
    """
    Task to cleanup the image conversion files after the task ends
    :param task_id: <string> id of the task to be cleaned up
    """
    task = ImageConversionTask.query.filter_by(id=task_id).first()
    if not task or not task.instance:
        return

    task.step = ImageConversionTask.STEP_CLEANING_UP
    doosradb.session.commit()

    ssh_manager = None
    try:
        ssh_manager = SSHManager(task.instance.ip_address, password=task.instance.password)
        ssh_manager.run_command("rm -rf /mnt/image_conversion/*")
    except Exception as ex:
        # Catching general exceptions here as Paramiko documentation is a little inconsistent with the exceptions they
        # generate. We can not let this task fail as it can cost us a dangling instance
        task.status = ImageConversionTask.STATUS_SUCCESSFUL
        task.message = str(ex)
        doosradb.session.commit()
        return
    finally:
        if ssh_manager:
            ssh_manager.close_ssh_connection()

    task.status = ImageConversionTask.STATUS_SUCCESSFUL
    task.step = ImageConversionTask.STEP_PROCESS_COMPLETED
    doosradb.session.commit()


@celery.task(name="ic_get_image_size", queue="image_conversion_queue")
def get_image_size(cloud_id, region, bucket_name, image_name, image_format):
    """
    Get the size of image to convert. This task will get the size using object's HEAD data using S3 APIs
    :param cloud_id: <string> cloud ID for which the image is being converted (for credentials)
    :param region: <string> region in which the COS bucket resides
    :param bucket_name: <string> bucket name in which the image resides
    :param image_name: <string> Name of the image
    :return: <int> Image size in MBs
    """
    cloud = IBMCloud.query.filter_by(id=cloud_id).first()
    if not cloud:
        return

    client = ibm_boto3.client(
        service_name='s3', ibm_api_key_id=decrypt_api_key(cloud.api_key),
        ibm_service_instance_id=cloud.service_credentials.resource_instance_id,
        ibm_auth_endpoint="https://iam.cloud.ibm.com/identity/token",
        config=Config(signature_version="oauth"),
        endpoint_url="https://s3.{region}.cloud-object-storage.appdomain.cloud".format(region=region))

    response = client.head_object(
        Bucket=bucket_name,
        Key="{image_name}.{image_format}".format(image_name=image_name, image_format=image_format)
    )
    if not response.get("ResponseMetadata") or not response["ResponseMetadata"].get("HTTPHeaders") \
            or not response["ResponseMetadata"]["HTTPHeaders"].get("content-length"):
        return

    return int(int(response["ResponseMetadata"]["HTTPHeaders"]["content-length"]) / 1000000)
