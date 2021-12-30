import json

from flask import current_app, request, Response, jsonify

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import DELETING
from doosra.ibm.ssh_keys import ibm_ssh_keys
from doosra.ibm.ssh_keys.consts import SSH_KEY_CREATE, SSH_KEY_DELETE
from doosra.ibm.ssh_keys.schemas import ibm_create_ssh_key_schema
from doosra.models import IBMCloud, IBMSshKey, IBMTask
from doosra.validate_json import validate_json


@ibm_ssh_keys.route('/ssh_keys', methods=['GET'])
@authenticate
def list_ibm_ssh_keys(user_id, user):
    """
    Get IBM ssh keys
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    ssh_keys_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        for ssh_key in ibm_cloud.ssh_keys.all():
            ssh_keys_list.append(ssh_key.to_json())

    if not ssh_keys_list:
        return Response(status=204)

    return Response(json.dumps(ssh_keys_list), mimetype='application/json')


@ibm_ssh_keys.route('/ssh_keys/<ssh_key_id>', methods=['GET'])
@authenticate
def get_ibm_ssh_key(user_id, user, ssh_key_id):
    """
    Get IBM ssh keys
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ssh_key = doosradb.session.query(IBMSshKey).filter_by(id=ssh_key_id).first()
    if not ssh_key:
        current_app.logger.info("No IBM ssh key found with ID {id}".format(id=ssh_key_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(
        id=ssh_key.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=ssh_key.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return Response(json.dumps(ssh_key.to_json()), mimetype="application/json")


@ibm_ssh_keys.route('/ssh_keys', methods=['POST'])
@validate_json(ibm_create_ssh_key_schema)
@authenticate
def create_ibm_ssh_key(user_id, user):
    """
    Add an IBM ssh key
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ssh_key

    data = request.get_json(force=True)
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud project found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    ssh_key_name = doosradb.session.query(IBMSshKey).filter_by(
        name=data['name'], cloud_id=data['cloud_id'], region=data.get('region')).first()
    if ssh_key_name:
        return Response("Error conflicting ssh key name", status=409)

    ssh_public_key = doosradb.session.query(IBMSshKey).filter_by(
        public_key=data['public_key'], cloud_id=data['cloud_id'], region=data['region']).first()
    if ssh_public_key:
        return Response("Error conflicting ssh public key", status=409)

    task = IBMTask(task_create_ssh_key.delay(data, user_id, user.project.id).id, "SSH-KEY", "ADD", cloud.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(SSH_KEY_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_ssh_keys.route('/ssh_keys/<ssh_key_id>', methods=['DELETE'])
@authenticate
def delete_ibm_ssh_key(user_id, user, ssh_key_id):
    """
    Delete an IBM ssh_keys
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param ssh: ssh_key_id for ssh keys
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.ssh_key_tasks import task_delete_ssh_key_workflow

    ssh_key = doosradb.session.query(IBMSshKey).filter_by(id=ssh_key_id).first()
    if not ssh_key:
        current_app.logger.info("No IBM ssh key found with ID {id}".format(id=ssh_key_id))
        return Response(status=404)

    if ssh_key.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not ssh_key.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="SSH-KEY", region=ssh_key.region, action="DELETE",
        cloud_id=ssh_key.ibm_cloud.id, resource_id=ssh_key.id)

    doosradb.session.add(task)
    ssh_key.status = DELETING
    doosradb.session.commit()

    task_delete_ssh_key_workflow.delay(task_id=task.id, cloud_id=ssh_key.ibm_cloud.id,
                                       region=ssh_key.region, ssh_key_id=ssh_key.id)

    current_app.logger.info(SSH_KEY_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
