from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.images.consts import COS_IMAGE_REF
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMCloud, IBMImage


def configure_image(data):
    ibm_image = None
    ibm_cloud = IBMCloud.query.get(data["cloud_id"])
    if not ibm_cloud:
        current_app.logger.debug("IBM cloud with ID {} not found".format(data["cloud_id"]))
        return
    try:
        ibm_manager = IBMManager(ibm_cloud, data['region'])
        existing_image = ibm_manager.rias_ops.fetch_ops.get_all_images(name=data['name'], visibility="private")
        if existing_image:
            raise IBMInvalidRequestError("IBM image with name '{}' already configured".format(data['name']))

        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])
        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))
        existing_resource_group = existing_resource_group[0].get_existing_from_db() or existing_resource_group[0]

        operating_system = ibm_manager.rias_ops.fetch_ops.get_all_operating_systems(name=data['operating_system'])
        if not operating_system:
            raise IBMInvalidRequestError("Operating System {name} not found".format(name=data['operating_system']))

        ibm_image = IBMImage(
            name=data['name'], visibility="private",
            image_template_path=COS_IMAGE_REF.format(region=data['region'], bucket=data['bucket'],
                                                     image_template=data['image_template']), region=data['region'])
        ibm_image.ibm_cloud = ibm_cloud
        ibm_image.ibm_resource_group = existing_resource_group
        ibm_image.operating_system = operating_system[0].make_copy().add_update_db()

        ibm_image = ibm_image.make_copy().add_update_db()

        ibm_manager.rias_ops.create_image(ibm_image)
        existing_image = ibm_manager.rias_ops.fetch_ops.get_all_images(name=data['name'], visibility="private")
        if not existing_image:
            raise IBMInvalidRequestError("Failed to configure IBM Image {}".format(ibm_image.name))

        ibm_image.resource_id = existing_image[0].resource_id
        ibm_image.size = existing_image[0].size
        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_image.ibm_cloud.status = INVALID
        if ibm_image:
            ibm_image.status = ERROR_CREATING
        doosradb.session.commit()

    else:
        ibm_image.status = CREATED
        doosradb.session.commit()

    return ibm_image


def delete_image(image):
    """
    This request deletes an image from IBM cloud
    :return:
    """
    current_app.logger.info("Deleting IBM image '{name}' on IBM Cloud".format(name=image.name))
    try:
        ibm_manager = IBMManager(image.ibm_cloud, region=image.region)
        existing_image = ibm_manager.rias_ops.fetch_ops.get_all_images(name=image.name)
        if existing_image:
            ibm_manager.rias_ops.delete_image(existing_image[0])
        image.status = DELETED
        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            image.ibm_cloud.status = INVALID
        if image:
            image.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        image.status = DELETED
        doosradb.session.delete(image)
        doosradb.session.commit()
        return True
