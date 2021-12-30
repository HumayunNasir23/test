import json

from flask import current_app, jsonify, Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.gcp.instance import gcp_instance
from doosra.gcp.instance.consts import *
from doosra.gcp.instance.schemas import *
from doosra.models.gcp_models import GcpCloudProject, GcpInstance, GcpTask, GcpVpcNetwork
from doosra.validate_json import validate_json


@gcp_instance.route('/cloud_projects/<cloud_project_id>/instances', methods=['POST'])
@validate_json(add_instance_schema)
@authenticate
def add_gcp_instance(user_id, user, cloud_project_id):
    """
    Create Instance on selected cloud
    """
    from doosra.tasks.other.gcp_tasks import task_create_instance

    data = request.get_json(force=True)
    project = doosradb.session.query(GcpCloudProject).filter_by(id=data['cloud_project_id']).first()
    if not project:
        current_app.logger.info("No GCP cloud project found with ID {id}".format(id=data['cloud_project_id']))
        return Response(status=404)

    instance = doosradb.session.query(GcpInstance).filter_by(name=data['name'], cloud_project_id=project.id).first()
    if instance:
        return Response("INSTANCE_NAME_CONFLICT", status=409)

    if data.get('interfaces'):
        for interface in data.get('interfaces'):
            vpc = doosradb.session.query(GcpVpcNetwork).filter_by(id=interface['vpc_id']).first()
            if not vpc:
                return Response("VPC_NOT_FOUND", status=404)

            subnet = vpc.subnets.filter_by(id=interface['subnetwork_id']).first()
            if not subnet:
                return Response("SUBNET_NOT_FOUND", status=404)

    task = GcpTask(
        task_create_instance.delay(project.id, data.get("zone"), data.get("name"), data.get("machine_type"),
                                   data.get("description"), data.get('network_tags'), data.get("interfaces"),
                                   data.get("disks")).id, "INSTANCE", "ADD", project.gcp_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_instance.route('/cloud_projects/<cloud_project_id>/instances/<instance_id>', methods=['DELETE'])
@authenticate
def delete_instance(user_id, user, instance_id, cloud_project_id):
    """
    Delete an Instance on selected cloud
    """
    from doosra.tasks.other.gcp_tasks import task_delete_instance

    instance = doosradb.session.query(GcpInstance).filter_by(id=instance_id).first()
    if not instance:
        current_app.logger.info("No Instance found with ID {id}".format(id=instance_id))
        return Response("No Instance Found.", status=404)

    if not instance.gcp_cloud_project.user_project_id == user.project.id:
        return Response("INVALID_CLOUD", status=400)

    if instance.gcp_instance_groups:
        current_app.logger.info("Instance with ID {} has instance groups".format(instance_id))
        return Response("Instance has InstanceGroup attached. Delete them first.", status=400)

    task = GcpTask(task_delete_instance.delay(instance.id).id, "INSTANCE", "DELETE",
                   instance.gcp_cloud_project.gcp_cloud.id, instance.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(INSTANCE_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_instance.route('/cloud_projects/<cloud_project_id>/instances', methods=['GET'])
@authenticate
def get_instances(user_id, user, cloud_project_id):
    """
    Get Instances for a cloud project
    """
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=cloud_project_id, user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    instances = project.instances.all()
    if not instances:
        return Response(status=204)

    instances_list = list()
    for vpc in instances:
        instances_list.append(vpc.to_json())

    return Response(json.dumps(instances_list), mimetype='application/json')


@gcp_instance.route('/cloud_projects/<cloud_project_id>/instances/<instance_id>', methods=['GET'])
@authenticate
def get_instance(user_id, user, cloud_project_id, instance_id):
    """
    Get Instance for a cloud project
    """
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=cloud_project_id, user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP Cloud project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    instance = project.instances.filter_by(id=instance_id).first()
    if not instance:
        return Response(status=204)

    return Response(json.dumps(instance.to_json()), mimetype='application/json')
