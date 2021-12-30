import json

from flask import current_app, request, Response, jsonify

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import DELETING
from doosra.ibm.load_balancers import ibm_load_balancers
from doosra.ibm.load_balancers.consts import LB_DELETE, LB_CREATE
from doosra.ibm.load_balancers.schemas import ibm_create_load_balancer_schema
from doosra.models import IBMCloud, IBMLoadBalancer, IBMSubnet, IBMTask, IBMVpcNetwork
from doosra.validate_json import validate_json


@ibm_load_balancers.route('/load_balancers', methods=['GET'])
@authenticate
def list_ibm_load_balancers(user_id, user):
    """
    Get IBM VPC Load Balancers
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    load_balancers_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        for load_balancer in ibm_cloud.load_balancers.all():
            load_balancers_list.append(load_balancer.to_json())

    if not load_balancers_list:
        return Response(status=204)

    return Response(json.dumps(load_balancers_list), mimetype='application/json')


@ibm_load_balancers.route('/load_balancers/<load_balancer_id>', methods=['GET'])
@authenticate
def get_ibm_load_balancer(user_id, user, load_balancer_id):
    """
    Get IBM VPC Load Balancer
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    """
    load_balancer = doosradb.session.query(IBMLoadBalancer).filter_by(id=load_balancer_id).first()
    if not load_balancer:
        current_app.logger.info("No IBM Load Balancer found with ID {id}".format(id=load_balancer_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(
        id=load_balancer.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=load_balancer.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return Response(json.dumps(load_balancer.to_json()), mimetype="application/json")


@ibm_load_balancers.route('/load_balancers', methods=['POST'])
@validate_json(ibm_create_load_balancer_schema)
@authenticate
def create_ibm_load_balancer(user_id, user):
    """
    Add an IBM load balancer
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_load_balancer

    data = request.get_json(force=True)
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud project found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=data["vpc_id"], cloud_id=data["cloud_id"]).first()
    if not vpc:
        current_app.logger.info("No IBM VPC found with ID {id}".format(id=data['vpc_id']))
        return Response(status=404)

    load_balancer = doosradb.session.query(IBMLoadBalancer).filter_by(
        name=data['name'], cloud_id=data['cloud_id'], region=vpc.region).first()

    if load_balancer:
        return Response("ERROR_CONFLICTING_LOAD_BALANCER_NAME", status=409)

    for subnet in data['subnets']:
        subnet = IBMSubnet.query.get(subnet['id'])
        if not subnet:
            current_app.logger.info("No IBM Subnet with ID {id}".format(id=subnet['id']))
            return Response(status=404)

    task = IBMTask(
        task_create_ibm_load_balancer.delay(data, user_id, user.project.id).id, "LOAD-BALANCER", "ADD", cloud.id,
        request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(LB_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_load_balancers.route('/load_balancers/<load_balancer_id>', methods=['DELETE'])
@authenticate
def delete_ibm_load_balancer(user_id, user, load_balancer_id):
    """
    Delete an IBM load balancer
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param loadBalancer_id: loadBalancer_id for load balancer
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.load_balancer_tasks import task_delete_ibm_load_balancer_workflow

    load_balancer = doosradb.session.query(IBMLoadBalancer).filter_by(id=load_balancer_id).first()
    if not load_balancer:
        current_app.logger.info("No IBM load balancer found with ID {id}".format(id=load_balancer_id))
        return Response(status=404)

    if load_balancer.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not load_balancer.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="LOAD-BALANCER", region=load_balancer.region, action="DELETE",
        cloud_id=load_balancer.ibm_cloud.id, resource_id=load_balancer.id)

    doosradb.session.add(task)
    load_balancer.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_load_balancer_workflow.delay(task_id=task.id, cloud_id=load_balancer.ibm_cloud.id,
                                                 region=load_balancer.region,
                                                 load_balancer_id=load_balancer.id)

    current_app.logger.info(LB_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
