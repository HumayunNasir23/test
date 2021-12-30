import json

from flask import current_app, request, Response, jsonify

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import DELETING
from doosra.ibm.floating_ips import ibm_floating_ips
from doosra.ibm.floating_ips.consts import FLOATING_IP_CREATE, FLOATING_IP_DELETE
from doosra.ibm.floating_ips.schemas import ibm_create_floating_ip_schema
from doosra.models import IBMCloud, IBMFloatingIP, IBMTask
from doosra.validate_json import validate_json


@ibm_floating_ips.route('/floating_ips', methods=['GET'])
@authenticate
def get_ibm_floating_ips(user_id, user):
    """
    Get IBM floating ips
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {user_id}".format(user_id=user.project.id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    floating_ips = ibm_cloud.floating_ips.all()
    if not floating_ips:
        return Response(status=204)

    floating_ips_list = list()
    for floating_ip in floating_ips:
        floating_ips_list.append(floating_ip.to_json())

    return Response(json.dumps(floating_ips_list), mimetype='application/json')


@ibm_floating_ips.route('/floating_ips/<floating_ip_id>', methods=['GET'])
@authenticate
def get_ibm_floating_ip(user_id, user, floating_ip_id):
    """
    Get IBM floating ips
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    floating_ip = doosradb.session.query(IBMFloatingIP).filter_by(id=floating_ip_id).first()
    if not floating_ip:
        current_app.logger.info("No IBM floating ip found with ID {id}".format(id=floating_ip_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(
        id=floating_ip.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=floating_ip.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return Response(json.dumps(floating_ip.to_json()), mimetype="application/json")


@ibm_floating_ips.route('/floating_ips', methods=['POST'])
@validate_json(ibm_create_floating_ip_schema)
@authenticate
def create_ibm_floating_ip(user_id, user):
    """
    Add an IBM floating ip
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_floating_ip

    data = request.get_json(force=True)
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud project found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_create_floating_ip.delay(data, user_id, user.project.id).id, "FLOATING-IP", "ADD", cloud.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(FLOATING_IP_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_floating_ips.route('/floating_ips/<floating_ip_id>', methods=['DELETE'])
@authenticate
def delete_ibm_floating_ip(user_id, user, floating_ip_id):
    """
    Delete an IBM floating ip
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param floating ip: floating_ip_id for floating ip
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.floating_ip_tasks import task_delete_ibm_floating_ip_workflow

    floating_ip = doosradb.session.query(IBMFloatingIP).filter_by(id=floating_ip_id).first()
    if not floating_ip:
        current_app.logger.info("No IBM floating ip found with ID {id}".format(id=floating_ip_id))
        return Response(status=404)

    if floating_ip.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not floating_ip.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="FLOATING-IP", region=floating_ip.region, action="DELETE",
        cloud_id=floating_ip.ibm_cloud.id, resource_id=floating_ip.id)

    doosradb.session.add(task)
    floating_ip.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_floating_ip_workflow.delay(task_id=task.id, cloud_id=floating_ip.ibm_cloud.id,
                                               region=floating_ip.region, floating_ip_id=floating_ip.id)

    current_app.logger.info(FLOATING_IP_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
