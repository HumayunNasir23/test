import json
import logging
import os
import random
from copy import deepcopy

from doosra import db as doosradb
from doosra.common.clients.ibm_clients import VolumesClient
from doosra.common.utils import decrypt_api_key, encrypt_api_key, get_volume_attachment_dict
from doosra.ibm.managers.operations.rias.consts import GENERATION, VERSION
from doosra.migration.data_migration.consts import CAPACITY, DATA_MIG_REQUIREMENTS, DISK_IDENTIFIER, \
    LARGEST_SECONDARY_VOLUMES_LIMIT, NAME, SVM_ENV, VOLUME, WINDOWS_MIG_REQ, NAS_MIG_CONSTS
from doosra.migration.data_migration.exceptions.exceptions import VolumeAttachmentException
from doosra.migration.data_migration.utils import return_class
from doosra.models import IBMCloud, IBMVolumeAttachment, IBMVolume, IBMVolumeProfile, IBMInstance
from doosra.models.migration_models import SecondaryVolumeMigrationTask

LOGGER = logging.getLogger("doosra/tasks/ibm/volume_extraction_utils.py")


def attach_additional_volume(volumes_json, disk_name, ibm_cloud_id, region):
    """
    Add additional volume for secondary volume migration
    """
    ibm_cloud_obj = doosradb.session.query(IBMCloud).filter_by(id=ibm_cloud_id).first()
    if not ibm_cloud_obj:
        raise VolumeAttachmentException

    volume_client = VolumesClient(ibm_cloud_id)
    higher_capacity = 10
    new_volume_json = deepcopy(volumes_json[0])
    for volume_json in volumes_json:
        if int(volume_json[CAPACITY]) > higher_capacity:
            higher_capacity = int(volume_json[CAPACITY])
            new_volume_json = deepcopy(volume_json)

    higher_capacity = higher_capacity - DISK_IDENTIFIER if higher_capacity == LARGEST_SECONDARY_VOLUMES_LIMIT else \
        higher_capacity + DISK_IDENTIFIER
    new_volume_json[VOLUME][CAPACITY] = higher_capacity
    existing_volume = volume_client.list_volumes(region=region, name=disk_name)
    if existing_volume:
        for volume_index in range(100):
            disk_name += str(random.randrange(100))
            disk_name = disk_name[-60:]
            existing_volume = volume_client.list_volumes(region=region, name=disk_name)
            if not existing_volume:
                break

    new_volume_json[NAME] = SVM_ENV + disk_name
    new_volume_json["is_migration_enabled"] = False
    new_volume_json["volume_index"] = None
    new_volume_json[VOLUME][NAME] = SVM_ENV + disk_name
    return new_volume_json


def insert_volume_in_db(instance_id, volumes_json, region, cloud_id):
    """
    Insert Volumes in DB
    """
    ibm_instance = IBMInstance.query.get(instance_id)
    for volume_json in volumes_json:
        ibm_volume_attachment = IBMVolumeAttachment(
            name=volume_json["name"],
            type_=volume_json.get("type") or "data",
            is_delete=volume_json["is_delete"],
            is_migration_enabled=volume_json.get("is_migration_enabled"),
            volume_index=volume_json.get("volume_index")
        )
        ibm_volume = IBMVolume(
            name=volume_json["volume"]["name"],
            capacity=volume_json["volume"].get("capacity") or 100,
            zone=volume_json["volume"]["zone"],
            region=region,
            iops=volume_json.get("iops") or 3000,
            encryption=volume_json.get("encryption") or "provider_managed",
            cloud_id=cloud_id,
            original_capacity=volume_json["volume"].get("original_capacity")
        )
        volume_profile = IBMVolumeProfile(
            name=volume_json["volume"]["profile"]["name"] or "general-profile",
            region=region,
            cloud_id=cloud_id)
        volume_profile = volume_profile.get_existing_from_db() or volume_profile
        ibm_volume.volume_profile = volume_profile.make_copy()
        ibm_volume_attachment.volume = ibm_volume
        ibm_instance.volume_attachments.append(ibm_volume_attachment)
        doosradb.session.add(ibm_volume_attachment)
        doosradb.session.commit()


def construct_user_data_script(instance, ibm_cloud, region, instance_id):
    """
    Create user_data script from COS files and a disk for linux helper migration.
    Fifth Volume is added directly to instance as IBM is supporting more than four volumes with all profiles.
    :return:
    """
    if len(instance.get("volume_attachments") or []) <= 0:
        return

    api_key = decrypt_api_key(ibm_cloud.api_key)

    # sorting in ascending order by volume capacity
    volumes = instance["volume_attachments"]
    sorted_volumes = sorted(volumes, key=lambda i: i['capacity'])
    instance["volume_attachments"] = sorted_volumes

    ## TODO: This is what was consider for linux A1
    attach_volumes = ' '.join(
        [str(volume["volume_index"]) for volume in instance["volume_attachments"] if
         volume.get("volume_index") and volume.get("is_migration_enabled")])
    try:
        attach_volumes_capacity = ' '.join(
            [str(volume["capacity"]) for volume in instance["volume_attachments"] if
             volume.get("volume_index") and volume.get("is_migration_enabled")])
    except KeyError:
        return

    ## TODO: This was considered for windows A2
    window_vhds_index = [volume["volume_index"] for volume in instance["volume_attachments"] if volume.get("volume_index")]
    ## TODO: Need to consider anyof(A1, A2)

    volume_mig_task = SecondaryVolumeMigrationTask(instance_id=instance_id)
    doosradb.session.add(volume_mig_task)
    doosradb.session.commit()

    if "WINDOWS" in instance.get("original_operating_system_name", "").upper() or \
            "WINDOWS" in instance.get("original_image", "").upper() or \
            "WINDOWS" in instance["image"].get("public_image", "").upper() or \
            "WINDOWS" in instance["image"].get("vpc_image_name", "").upper():
        web_hook_uri = os.environ.get(
            "VPCPLUS_LINK") + "v1/ibm/instances/secondary-volume-migration/windows/" + volume_mig_task.id
        user_data_script = WINDOWS_MIG_REQ.format(API_KEY=api_key, REGION=region,
                                                  BUCKET=instance["image"]["bucket_name"],
                                                  VHDS_INDEX=", ".join(repr(item) for item in window_vhds_index),
                                                  INSTANCE_ID=instance_id, WEB_HOOK_URI=web_hook_uri,
                                                  VERSION=VERSION, GENERATION=GENERATION)
    else:
        new_volume_json = attach_additional_volume(instance["volume_attachments"], instance_id, ibm_cloud.id, region)

        operating_system = return_class(
            instance["image"].get("public_image") or instance["image"].get("vpc_image_name") or
            instance.get("original_operating_system_name"))

        packages = operating_system.qemu_package
        for pkg in operating_system.PACKAGES:
            packages = packages + " " + pkg

        data_mig_req_string = DATA_MIG_REQUIREMENTS.format(
            SVM_WORKING_DISK=str(new_volume_json[VOLUME][CAPACITY]) + "G",
            ATTACHED_VOLUME_COUNT=attach_volumes,
            ATTACHED_VOLUMES_CAPACITY=attach_volumes_capacity,
            INSTANCE_NAME=instance["name"],
            VOLUME_NAME=new_volume_json["name"],
            PACKAGES=packages,
            REGION=region,
            VERSION=VERSION,
            BUCKET=instance["image"]["bucket_name"],
            WEB_HOOK_URI=os.environ.get(
                "VPCPLUS_LINK") + "v1/ibm/instances/secondary_volume_migration/" + volume_mig_task.id,
            API_KEY=api_key,
        )
        user_data_script = "{data_mig_req_string}\n{packages}".format(
            data_mig_req_string=data_mig_req_string,
            packages=operating_system.bash_installation_string
        )
        insert_volume_in_db(instance_id, volumes_json=[new_volume_json], region=region, cloud_id=ibm_cloud.id)

    ibm_instance = IBMInstance.query.get(instance_id)
    if ibm_instance.user_data:
        user_data_script = f"{decrypt_api_key(ibm_instance.user_data)}\n{user_data_script}"
    ibm_instance.user_data = encrypt_api_key(user_data_script)
    doosradb.session.commit()
    LOGGER.info(f"Volume Migration Requirements Added for instance {instance_id} Secondary Migration Data")


def construct_nas_migration_user_data(instance, region, instance_id, cloud_id):
    """
    Create a User Data Script for NAS Migration and create Volumes as per NAS Volumes
    """
    volume_attachments = []
    for ind_, disk in enumerate(instance["nas_migration_info"]["cm_meta_data"].get("disks", [])):
        volume_attachments.append(get_volume_attachment_dict(capacity=disk["size"][:-1], zone=instance["zone"],
                                                             name=instance["name"], index_=ind_))

    insert_volume_in_db(instance_id, volumes_json=volume_attachments, region=region, cloud_id=cloud_id)
    migration_host = os.environ.get("DB_MIGRATION_CONTROLLER_HOST")
    if migration_host.find("https://") != -1:
        migration_host = migration_host.replace("https://", "")
    elif migration_host.find("https://") != -1:
        migration_host = migration_host.replace("http://", "")
    if migration_host.endswith("/"):
        migration_host = migration_host[:-1]

    nas_migration_script = NAS_MIG_CONSTS.format(user_id=instance["nas_migration_info"]["cm_meta_data"]["user_id"],
                                                 migration_host=migration_host,
                                                 vpc_backend_host=os.environ.get("VPCPLUS_LINK"),
                                                 trg_migrator_name=f"trg-{region}-{instance['name']}",
                                                 src_migrator_name=instance["nas_migration_info"]["cm_meta_data"][
                                                     "migrator_name"],
                                                 instance_type=os.environ.get("DB_MIGRATION_INSTANCE_TYPE"),
                                                 disks=json.dumps(
                                                     instance["nas_migration_info"]["cm_meta_data"]["disks"]))

    ibm_instance = IBMInstance.query.get(instance_id)
    ibm_instance.user_data = encrypt_api_key(nas_migration_script)
    doosradb.session.commit()
    LOGGER.info(f"Volume Migration Requirements Added for instance {instance_id} NAS Migration Data")
