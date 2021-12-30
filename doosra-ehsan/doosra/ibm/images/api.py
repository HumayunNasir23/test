import json

from flask import current_app, jsonify, Response, request

from doosra.common.consts import DELETING
from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.ibm.images.consts import *
from doosra.ibm.images.schemas import ibm_image_migration_update_schema, ibm_image_schema
from doosra.ibm.instances import ibm_instances
from doosra.models import IBMImage, IBMCloud, IBMTask, ImageConversionTask
from doosra.validate_json import validate_json


@ibm_instances.route('/custom_images', methods=['POST'])
@validate_json(ibm_image_schema)
@authenticate
def add_ibm_image(user_id, user):
    """
    Add IBM Image
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_image

    data = request.get_json(force=True)

    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    existing_image = doosradb.session.query(IBMImage).filter_by(name=data['name'], cloud_id=data['cloud_id'],
                                                                region=data.get('region')).first()
    if existing_image:
        return Response("Error conflicting image names", status=409)

    task = IBMTask(task_create_ibm_image.delay(data, user_id, user.project.id).id, "IMAGE", "ADD", cloud.id,
                   request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(IMAGE_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_instances.route('/custom_images', methods=['GET'])
@authenticate
def list_ibm_images(user_id, user):
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    images_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        images = ibm_cloud.images.filter_by(visibility='private').all()
        for image in images:
            images_list.append(image.to_json())

    if not images_list:
        return Response(status=204)

    return Response(json.dumps(images_list), mimetype='application/json')


@ibm_instances.route('/custom_images/<image_id>', methods=['GET'])
@authenticate
def get_ibm_image(user_id, user, image_id):
    """
     Get IBM ssh keys
     :param user_id: ID of the user initiating the request
     :param user: object of the user initiating the request
     """
    image = doosradb.session.query(IBMImage).filter_by(id=image_id).first()
    if not image:
        current_app.logger.info("No IBM ssh key found with ID {id}".format(id=image_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(
        id=image.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=image.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return Response(json.dumps(image.to_json()), mimetype="application/json")


@ibm_instances.route('/custom_images/<image_id>', methods=['DELETE'])
@authenticate
def delete_ibm_image(user_id, user, image_id):
    """
    Delete an IBM ssh_keys
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param ssh: ssh_key_id for ssh keys
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.image_tasks import task_delete_image_workflow

    image = doosradb.session.query(IBMImage).filter_by(id=image_id).first()
    if not image:
        current_app.logger.info("No IBM image found with ID {id}".format(id=image_id))
        return Response(status=404)

    if image.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not image.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="IMAGE", region=image.region, action="DELETE",
        cloud_id=image.ibm_cloud.id, resource_id=image.id)

    doosradb.session.add(task)
    image.status = DELETING
    doosradb.session.commit()

    task_delete_image_workflow.delay(task_id=task.id, cloud_id=image.ibm_cloud.id,
                                     region=image.region, image_id=image.id)

    current_app.logger.info(IMAGE_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_instances.route('/image_conversion/<task_id>', methods=['PATCH'])
@validate_json(ibm_image_migration_update_schema)
def update_image_conversion_task(task_id):
    """
    Webhook for image conversion script to update statuses
    :param task_id: <string> id of the ImageConversionTask to be updated

    :return: requests.Response object
    """
    task = ImageConversionTask.query.filter_by(id=task_id).first()
    if not task:
        return Response(status=204)

    data = request.get_json(force=True)

    if data["status"] == ImageConversionTask.STATUS_FAILED:
        task.status = ImageConversionTask.STATUS_FAILED
        task.message = data["message"]
        doosradb.session.commit()
        return Response(status=200)

    if data["step"] == "DOWNLOAD":
        task.step = ImageConversionTask.STEP_IMAGE_CONVERTING
    elif data["step"] == "CONVERT":
        task.step = ImageConversionTask.STEP_IMAGE_VALIDATING
    elif data["step"] == "VALIDATE":
        task.step = ImageConversionTask.STEP_IMAGE_UPLOADING
    elif data["step"] == "UPLOAD":
        task.step = ImageConversionTask.STEP_PENDING_CLEANUP
    doosradb.session.commit()

    return Response(status=200)
