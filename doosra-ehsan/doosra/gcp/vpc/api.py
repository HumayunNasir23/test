import json

from flask import current_app, jsonify, Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.common.utils import validate_subnets
from doosra.gcp.vpc import gcp_vpc
from doosra.gcp.vpc.consts import *
from doosra.gcp.vpc.schemas import *
from doosra.models.gcp_models import GcpCloudProject, GcpTask, GcpVpcNetwork
from doosra.validate_json import validate_json


@gcp_vpc.route('/cloud_projects/<cloud_project_id>/vpcs', methods=['GET'])
@authenticate
def get_vpc_networks(user_id, user, cloud_project_id):
    """
    Get VPC networks for a cloud project
    """
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=cloud_project_id, user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    vpc_networks = project.vpc_networks.all()
    if not vpc_networks:
        return Response(status=204)

    vpc_list = list()
    for vpc in vpc_networks:
        vpc_list.append(vpc.to_json())

    return Response(json.dumps(vpc_list), mimetype='application/json')


@gcp_vpc.route('/cloud_projects/<cloud_project_id>/vpcs/<vpc_id>', methods=['GET'])
@authenticate
def get_vpc_network(user_id, user, cloud_project_id, vpc_id):
    """
    Get VPC networks for a cloud project
    """
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=cloud_project_id, user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    vpc_network = project.vpc_networks.filter_by(id=vpc_id).first()
    if not vpc_network:
        return Response(status=204)

    return Response(json.dumps(vpc_network.to_json()), mimetype='application/json')


@gcp_vpc.route('/cloud_projects/<cloud_project_id>/vpcs', methods=['POST'])
@validate_json(add_vpc_network_schema)
@authenticate
def add_vpc_network(user_id, user, cloud_project_id):
    """
    Deploy VPC network on selected cloud
    """
    from doosra.tasks.other.gcp_tasks import task_create_vpc_network

    data = request.get_json(force=True)
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=cloud_project_id, user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    vpc = doosradb.session.query(GcpVpcNetwork).filter_by(name=data['name'],
                                                          cloud_project_id=cloud_project_id).first()
    if vpc:
        return Response("ERROR_CONFLICTING_VPC_NAME", status=409)

    if data.get("subnets") and not validate_subnets(data.get('subnets')):
        return Response('INVALID_SUBNETS', status=400)

    task = GcpTask(
        task_create_vpc_network.delay(project.id, data.get("name"), data.get("description"), data.get("subnets")).id,
        "VPC", "ADD", project.gcp_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(VPC_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_vpc.route('/cloud_projects/<cloud_project_id>/vpcs/<vpc_id>', methods=['DELETE'])
@authenticate
def delete_vpc_network(user_id, user, vpc_id, cloud_project_id):
    """
    Delete VPC network on selected cloud
    """
    from doosra.tasks.other.gcp_tasks import task_delete_vpc_network

    vpc = doosradb.session.query(GcpVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        current_app.logger.info("No Google VPC found with ID {id}".format(id=vpc_id))
        return Response(status=404)

    if not vpc.gcp_cloud_project.user_project_id == user.project.id:
        return Response("INVALID_CLOUD", status=400)

    if vpc.name == "default":
        current_app.logger.info("VPC network 'default' cannot be deleted")
        return Response(status=400)

    task = GcpTask(task_delete_vpc_network.delay(vpc.id).id, "VPC", "DELETE", vpc.gcp_cloud_project.gcp_cloud.id,
                   vpc.id)
    doosradb.session.add(task)
    vpc.status = DELETING
    doosradb.session.commit()

    current_app.logger.info(VPC_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_vpc.route('/cloud_projects/<cloud_project_id>/vpcs/<vpc_id>', methods=['PATCH'])
@validate_json(update_vpc_network_schema)
@authenticate
def update_vpc_network(user_id, user, vpc_id, cloud_project_id):
    """
    Update Google VPC network with provided data
    """
    from doosra.tasks.other.gcp_tasks import task_update_vpc_network

    data = request.get_json(force=True)
    vpc = doosradb.session.query(GcpVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        current_app.logger.info("No VPC network found with ID {id}".format(id=vpc_id))
        return Response(status=404)

    if not vpc.gcp_cloud_project.user_project_id == user.project.id:
        return Response("INVALID_CLOUD", status=400)

    if data.get("subnets") and not validate_subnets(data.get('subnets')):
        return Response('INVALID_SUBNETS', status=400)

    task = GcpTask(task_update_vpc_network.delay(vpc.id, data.get("subnets")).id, "VPC", "UPDATE",
                   vpc.gcp_cloud_project.gcp_cloud.id, vpc.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(VPC_UPDATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_vpc.route('/cloud_projects/<cloud_project_id>/vpcs/<vpc_id>/tags', methods=['GET'])
@authenticate
def get_network_tags(user_id, user, cloud_project_id, vpc_id):
    """
    Get list of network tags allocated to VMs
    """
    vpc = doosradb.session.query(GcpVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        current_app.logger.info("No VPC network found with ID {id}".format(id=vpc_id))
        return Response(status=404)

    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=vpc.gcp_cloud_project.id, user_project_id=user.project.id).first()
    if not project:
        return Response("INVALID_CLOUD_PROJECT", status=400)

    tags = vpc.tags.all()
    if not tags:
        return Response(status=204)

    tags_list = list()
    for tag in tags:
        tags_list.append(tag.to_json())

    return Response(json.dumps(tags_list), mimetype='application/json')
