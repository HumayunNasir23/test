import json

from flask import current_app, jsonify, Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import DELETING
from doosra.common.utils import validate_ip_range
from doosra.gcp.firewalls import gcp_firewalls
from doosra.gcp.firewalls.consts import *
from doosra.gcp.firewalls.schemas import *
from doosra.models.gcp_models import GcpCloudProject, GcpFirewallRule, GcpTask, GcpVpcNetwork
from doosra.validate_json import validate_json


@gcp_firewalls.route('/cloud_projects/<cloud_project_id>/firewalls', methods=['POST'])
@validate_json(add_firewall_rule_schema)
@authenticate
def add_firewall_rule(user_id, user, cloud_project_id):
    """
    Deploy Firewall rule on selected Google Cloud
    """
    from doosra.tasks.other.gcp_tasks import task_create_firewall_rule

    data = request.get_json(force=True)
    project = doosradb.session.query(GcpCloudProject).filter_by(
        id=data['cloud_project_id'], user_project_id=user.project.id).first()
    if not project:
        current_app.logger.info("No GCP cloud project found with ID {id}".format(id=data['cloud_project_id']))
        return Response(status=404)

    firewall_rule = doosradb.session.query(GcpFirewallRule).filter_by(
        name=data['name'], vpc_network_id=data['vpc_network_id']).first()
    if firewall_rule:
        return Response("ERROR_CONFLICTING_FIREWALL_NAME", status=409)

    vpc = doosradb.session.query(GcpVpcNetwork).filter_by(id=data['vpc_network_id']).first()
    if not vpc:
        return Response("VPC_NOT_FOUND", status=404)

    if data.get('ip_ranges'):
        for ip in data.get('ip_ranges'):
            if not validate_ip_range(ip):
                return Response('INVALID_IP_RANGE', status=400)

    task = GcpTask(
        task_create_firewall_rule.delay(vpc.id, data['name'], data).id, "FIREWALL", "ADD", project.gcp_cloud.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(FIREWALL_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_firewalls.route('/cloud_projects/<cloud_project_id>/firewalls/<firewall_id>', methods=['DELETE'])
@authenticate
def delete_firewall_rule(user_id, user, firewall_id, cloud_project_id):
    """
    Delete firewall rule on selected cloud
    """
    from doosra.tasks.other.gcp_tasks import task_delete_firewall_rule

    firewall = doosradb.session.query(GcpFirewallRule).filter_by(id=firewall_id).first()
    if not firewall:
        current_app.logger.info("No Google Firewall Rule found with ID {id}".format(id=firewall_id))
        return Response(status=404)

    if not user.project.id == firewall.gcp_vpc_network.gcp_cloud_project.user_project_id:
        return Response("INVALID_FIREWALL_RULE", status=400)

    firewall.status = DELETING
    doosradb.session.commit()

    task = GcpTask(task_delete_firewall_rule.delay(firewall.id).id, "FIREWALL", "DELETE",
                   firewall.gcp_vpc_network.gcp_cloud_project.gcp_cloud.id, firewall.id)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(FIREWALL_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@gcp_firewalls.route('/cloud_projects/<cloud_project_id>/firewalls', methods=['GET'])
@authenticate
def get_firewall_rules(user_id, user, cloud_project_id):
    """
    Get firewall rules
    :return:
    """
    cloud_project = doosradb.session.query(GcpCloudProject).filter_by(id=cloud_project_id,
                                                                      user_project_id=user.project.id).first()
    if not cloud_project:
        return Response("INVALID_CLOUD_PROJECT", status=404)

    firewall_rules_list = list()
    for vpc_network in cloud_project.vpc_networks.all():
        for firewall in vpc_network.firewall_rules.all():
            firewall_rules_list.append(firewall.to_json())

    if not firewall_rules_list:
        return Response(status=204)

    return Response(json.dumps(firewall_rules_list), mimetype='application/json')


@gcp_firewalls.route('/cloud_projects/<cloud_project_id>/firewalls/<firewall_id>', methods=['GET'])
@authenticate
def get_firewall_rule(user_id, user, firewall_id, cloud_project_id):
    """
    Get a firewall rule against a firewall_id
    :return:
    """
    firewall_rule = doosradb.session.query(GcpFirewallRule).filter_by(id=firewall_id).first()
    if not firewall_rule:
        return Response(status=404)

    if not user.project.id == firewall_rule.gcp_vpc_network.gcp_cloud_project.user_project_id:
        return Response("INVALID_FIREWALL_RULE", status=400)

    return Response(json.dumps(firewall_rule.to_json()), mimetype='application/json')
