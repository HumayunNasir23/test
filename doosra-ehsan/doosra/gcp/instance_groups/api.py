from flask import current_app, jsonify, request, Response, json

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.gcp.instance_groups import gcp_instance_groups
from doosra.gcp.instance_groups.schemas import *
from doosra.models.gcp_models import GcpCloudProject, GcpInstance, GcpInstanceGroup, GcpTask, GcpVpcNetwork
from doosra.validate_json import validate_json
from .consts import *


@gcp_instance_groups.route('/cloud_projects/<cloud_project_id>/vpcs/<vpc_id>/instance-groups', methods=['POST'])
@validate_json(add_instance_group_schema)
@authenticate
def create_instance_group(user_id, user, cloud_project_id, vpc_id):
    """
    Create instance group resource
    :return:
    """
    from doosra.tasks.other.gcp_tasks import task_create_instance_group

    data = request.get_json(force=True)
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=data['cloud_project_id'], user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP cloud project found with ID {id}".format(id=data['cloud_project_id']))
        return Response(status=404)

    vpc = doosradb.session.query(GcpVpcNetwork).filter_by(
        id=vpc_id, cloud_project_id=data['cloud_project_id']).first()
    if not vpc:
        return Response("VPC_NOT_FOUND", status=404)

    instance_group = doosradb.session.query(GcpInstanceGroup).filter_by(
        name=data['name'], vpc_network_id=vpc_id).first()
    if instance_group:
        return Response("ERROR_CONFLICTING_INSTANCE_GROUP_NAME", status=409)

    for instance in data.get('instances'):
        gcp_instance = doosradb.session.query(GcpInstance).filter_by(id=instance['instance_id']).first()
        if not gcp_instance:
            return Response("INSTANCE_NOT_FOUND", status=404)

    task = GcpTask(task_create_instance_group.delay(project.id, data.get("name"), data).id, "INSTANCE-GROUP", "ADD",
                   project.gcp_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(INSTANCE_GROUP_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_instance_groups.route('/cloud_projects/<cloud_project_id>/vpcs/<vpc_id>/instance-groups/<instance_group_id>',
                           methods=['DELETE'])
@authenticate
def delete_instance_group(user_id, user, cloud_project_id, vpc_id, instance_group_id):
    """
    Delete instance-group on selected cloud
    """
    from doosra.tasks.other.gcp_tasks import task_delete_instance_group

    instance_group = doosradb.session.query(GcpInstanceGroup).filter_by(id=instance_group_id).first()
    if not instance_group:
        current_app.logger.info("No Google 'Instance Group' found with ID {id}".format(id=instance_group_id))
        return Response(status=404)

    if not instance_group.gcp_vpc_network.gcp_cloud_project.user_project_id == user.project.id:
        return Response("INVALID_CLOUD", status=400)

    task = GcpTask(task_delete_instance_group.delay(instance_group.id).id, "INSTANCE-GROUP", "DELETE",
                   instance_group.gcp_vpc_network.gcp_cloud_project.gcp_cloud.id, instance_group.id)
    doosradb.session.add(task)
    instance_group.status = DELETING
    doosradb.session.commit()

    current_app.logger.info(INSTANCE_GROUP_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_instance_groups.route('/cloud_projects/<cloud_project_id>/vpcs/<vpc_id>/instance-groups', methods=['GET'])
@authenticate
def get_instance_groups(user_id, user, cloud_project_id, vpc_id):
    """
    Get Instance groups networks for a VPC
    """
    vpc = doosradb.session.query(GcpVpcNetwork).filter_by(id=vpc_id).first()
    if not vpc:
        current_app.logger.info("No GCP VPC found with ID {id}".format(id=vpc_id))
        return Response(status=404)

    if not user.project.id == vpc.gcp_cloud_project.user_project_id:
        return Response("INVALID_VPC", status=400)

    instance_groups = vpc.instance_groups.all()
    if not instance_groups:
        return Response(status=204)

    instance_groups_list = list()
    for vpc in instance_groups:
        instance_groups_list.append(vpc.to_json())

    return Response(json.dumps(instance_groups_list), mimetype='application/json')


@gcp_instance_groups.route('/cloud_projects/<cloud_project_id>/vpcs/<vpc_id>/instance-groups/<instance_group_id>',
                           methods=['GET'])
@authenticate
def get_instance_group(user_id, user, cloud_project_id, vpc_id, instance_group_id):
    """
    Get instance group resource
    """
    instance_group = doosradb.session.query(GcpInstanceGroup).filter_by(id=instance_group_id).first()
    if not instance_group:
        return Response(status=404)

    if not user.project.id == instance_group.gcp_vpc_network.gcp_cloud_project.user_project_id:
        return Response("INVALID_INSTANCE_GROUP_ID", status=400)

    return Response(json.dumps(instance_group.to_json()), mimetype='application/json')
