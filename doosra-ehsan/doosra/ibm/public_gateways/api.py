import json

from flask import current_app, jsonify, Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.ibm.public_gateways import ibm_public_gateways
from doosra.ibm.public_gateways.consts import *
from doosra.ibm.public_gateways.schemas import *
from doosra.models import IBMCloud, IBMPublicGateway, IBMTask, IBMVpcNetwork
from doosra.validate_json import validate_json


@ibm_public_gateways.route('/public_gateways', methods=['POST'])
@validate_json(ibm_public_gateway_schema)
@authenticate
def add_ibm_public_gateway(user_id, user):
    """
    Add IBM Public Gateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_public_gateway

    data = request.get_json(force=True)
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=data["vpc_id"], cloud_id=data["cloud_id"]).first()
    if not vpc:
        current_app.logger.info("No IBM VPC found with ID {id}".format(id=data['vpc_id']))
        return Response(status=404)

    public_gateway = doosradb.session.query(IBMPublicGateway).filter_by(
        name=data['name'], cloud_id=data['cloud_id'], region=vpc.region).first()

    if public_gateway:
        return Response("ERROR_CONFLICTING_PUBLIC_GATEWAY_NAME", status=409)

    task = IBMTask(
        task_create_ibm_public_gateway.delay(data.get("name"), vpc.id, data, user_id, user.project.id).id, "PUBLIC-GATEWAY", "ADD", cloud.id,
        request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(PUBLIC_GATEWAY_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_public_gateways.route('/public_gateways', methods=['GET'])
@authenticate
def list_ibm_public_gateways(user_id, user):
    """
    List all IBM Public Gateways
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    public_gateways_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        public_gateways = ibm_cloud.public_gateways.all()
        for public_gateway in public_gateways:
            public_gateways_list.append(public_gateway.to_json())

    if not public_gateways_list:
        return Response(status=204)

    return jsonify(public_gateways_list)


@ibm_public_gateways.route('/public_gateways/<public_gateway_id>', methods=['GET'])
@authenticate
def get_ibm_public_gateway(user_id, user, public_gateway_id):
    """
    Get IBM Security Group
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param public_gateway_id: ID for IBM Public Gateway
    :return: Response object from flask package
    """
    public_gateway = doosradb.session.query(IBMPublicGateway).filter_by(id=public_gateway_id).first()
    if not public_gateway:
        current_app.logger.info("No IBM Public Gateway found with ID {id}".format(id=public_gateway_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(
        id=public_gateway.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=public_gateway.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return jsonify(public_gateway.to_json())


@ibm_public_gateways.route('/public_gateways/<public_gateway_id>', methods=['DELETE'])
@authenticate
def delete_ibm_public_gateway(user_id, user, public_gateway_id):
    """
    Delete an IBM Public Gateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param public_gateway_id: public_gateway_id for Public Gateway
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.public_gateway_tasks import task_delete_public_gateway_workflow

    public_gateway = doosradb.session.query(IBMPublicGateway).filter_by(id=public_gateway_id).first()
    if not public_gateway:
        current_app.logger.info("No IBM public_gateway found with ID {id}".format(id=public_gateway_id))
        return Response(status=404)

    if public_gateway.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not public_gateway.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="PUBLIC_GATEWAY", region=public_gateway.region, action="DELETE",
        cloud_id=public_gateway.ibm_cloud.id, resource_id=public_gateway.id)

    doosradb.session.add(task)
    public_gateway.status = DELETING
    doosradb.session.commit()

    task_delete_public_gateway_workflow.delay(task_id=task.id, cloud_id=public_gateway.ibm_cloud.id,
                                              region=public_gateway.region, public_gateway_id=public_gateway.id)

    current_app.logger.info(PUBLIC_GATEWAY_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
