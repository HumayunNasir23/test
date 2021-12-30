import json

from flask import current_app, jsonify, request, Response

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import DELETING
from doosra.gcp.load_balancers import gcp_load_balancers
from doosra.gcp.load_balancers.consts import *
from doosra.gcp.load_balancers.schemas import *
from doosra.models.gcp_models import GcpCloudProject, GcpLoadBalancer, GcpInstanceGroup, GcpTask
from doosra.validate_json import validate_json


@gcp_load_balancers.route('/cloud_projects/<cloud_project_id>/load-balancers', methods=['POST'])
@validate_json(add_load_balancer_schema)
@authenticate
def create_instance_group(user_id, user, cloud_project_id):
    """
    Create load-balancer resource
    :return:
    """
    from doosra.tasks.other.gcp_tasks import task_create_load_balancer

    data = request.get_json(force=True)
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=data['cloud_project_id'], user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP cloud project found with ID {id}".format(id=data['cloud_project_id']))
        return Response(status=404)

    load_balancer = doosradb.session.query(GcpLoadBalancer).filter_by(name=data['name'],
                                                                      cloud_project_id=data['cloud_project_id']).first()
    if load_balancer:
        return Response("ERROR_CONFLICTING_LOAD_BALANCER_NAME", status=409)

    for backend_service in data.get('backend_services'):
        for backend in backend_service.get('backends'):
            instance_group = doosradb.session.query(GcpInstanceGroup).filter_by(id=backend['instance_group_id']).first()
            if not instance_group:
                return Response("INSTANCE_GROUP_NOT_FOUND", status=404)

    task = GcpTask(task_create_load_balancer.delay(project.id, data.get("name"), data).id, "LOAD-BALANCER", "ADD",
                   project.gcp_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(LOAD_BALANCER_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_load_balancers.route('/cloud_projects/<cloud_project_id>/load-balancers/<load_balancer_id>', methods=['DELETE'])
@authenticate
def delete_instance_group(user_id, user, cloud_project_id, load_balancer_id):
    """
    Delete load-balancer on selected cloud
    """
    from doosra.tasks.other.gcp_tasks import task_delete_load_balancer

    load_balancer = doosradb.session.query(GcpLoadBalancer).filter_by(id=load_balancer_id).first()
    if not load_balancer:
        current_app.logger.info("No Google 'Load-Balancer' found with ID {id}".format(id=load_balancer_id))
        return Response(status=404)

    if not load_balancer.gcp_cloud_project.user_project_id == user.project.id:
        return Response("INVALID_CLOUD", status=400)

    task = GcpTask(task_delete_load_balancer.delay(load_balancer.id).id, "LOAD-BALANCER", "DELETE",
                   load_balancer.gcp_cloud_project.gcp_cloud.id, load_balancer.id)
    doosradb.session.add(task)
    load_balancer.status = DELETING
    doosradb.session.commit()

    current_app.logger.info(LOAD_BALANCER_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_load_balancers.route('/cloud_projects/<cloud_project_id>/load-balancers', methods=['GET'])
@authenticate
def get_load_balancers(user_id, user, cloud_project_id):
    """
    Get Load balancers configured in a cloud project
    """
    load_balancer = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id).first()
    if not load_balancer:
        current_app.logger.info("No GCP Cloud Project found with ID {id}".format(id=cloud_project_id))
        return Response(status=404)

    if not user.project.id == load_balancer.gcp_cloud_project.user_project_id:
        return Response("INVALID_CLOUD_PROJECT", status=400)

    load_balancers = load_balancer.load_balancers.all()
    if not load_balancers:
        return Response(status=204)

    load_balancers_list = list()
    for load_balancer in load_balancers:
        load_balancers_list.append(load_balancer.to_json())

    return Response(json.dumps(load_balancers_list), mimetype='application/json')


@gcp_load_balancers.route('/cloud_projects/<cloud_project_id>/load-balancers/<load_balancer_id>', methods=['GET'])
@authenticate
def get_load_balancer(user_id, user, cloud_project_id, load_balancer_id):
    """
    Get instance group resource
    """
    load_balancer = doosradb.session.query(GcpLoadBalancer).filter_by(id=load_balancer_id).first()
    if not load_balancer:
        return Response(status=404)

    if not user.project.id == load_balancer.gcp_cloud_project.user_project_id:
        return Response("INVALID_LOAD_BALANCER_ID", status=400)

    return Response(json.dumps(load_balancer.to_json()), mimetype='application/json')
