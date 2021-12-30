import json

from flask import current_app, jsonify, Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.ibm.security_groups import ibm_security_groups
from doosra.ibm.security_groups.schemas import *
from doosra.models import IBMCloud, IBMTask, IBMSecurityGroup, IBMSecurityGroupRule, IBMVpcNetwork
from doosra.validate_json import validate_json
from .consts import *


@ibm_security_groups.route('/security-groups', methods=['POST'])
@validate_json(ibm_security_group_schema)
@authenticate
def add_ibm_security_group(user_id, user):
    """
    Add IBM Security Group
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_security_group

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

    security_group = doosradb.session.query(IBMSecurityGroup).filter_by(
        name=data['name'], cloud_id=data['cloud_id'], region=vpc.region).first()

    if security_group:
        return Response("ERROR_CONFLICTING_SECURITY_GROUP_NAME", status=409)

    task = IBMTask(
        task_create_ibm_security_group.delay(data.get("name"), vpc.id, data, user_id, user.project.id).id, "SECURITY-GROUP", "ADD", cloud.id,
        request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(SECURITY_GROUP_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_security_groups.route('/security-groups', methods=['GET'])
@authenticate
def list_ibm_security_groups(user_id, user):
    """
    List all IBM Security Groups
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    security_groups_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        security_groups = ibm_cloud.security_groups.all()
        for security_group in security_groups:
            security_groups_list.append(security_group.to_json())

    if not security_groups_list:
        return Response(status=204)

    return Response(json.dumps(security_groups_list), mimetype='application/json')


@ibm_security_groups.route('/security-groups/<security_group_id>', methods=['GET'])
@authenticate
def get_ibm_security_group(user_id, user, security_group_id):
    """
    Get IBM Security Group
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param security_group_id: ID for IBM Security Group
    :return: Response object from flask package
    """
    security_group = doosradb.session.query(IBMSecurityGroup).filter_by(id=security_group_id).first()
    if not security_group:
        current_app.logger.info("No IBM Security Group found with ID {id}".format(id=security_group_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=security_group.cloud_id,
                                                           project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=security_group.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return Response(json.dumps(security_group.to_json()), mimetype="application/json")


@ibm_security_groups.route('/security-groups/<security_group_id>', methods=['DELETE'])
@authenticate
def delete_ibm_security_group(user_id, user, security_group_id):
    """
    Delete an IBM Security Group
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param security_group_id: security_group_id for Security Group
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.security_group_tasks import task_delete_ibm_security_group_workflow

    security_group = doosradb.session.query(IBMSecurityGroup).filter_by(id=security_group_id).first()
    if not security_group:
        current_app.logger.info("No IBM Security Group found with ID {id}".format(id=security_group_id))
        return Response(status=404)

    if security_group.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not security_group.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if security_group.is_default:
        return Response("ERROR_DEFAULT_SECURITY_GROUP", status=400)

    task = IBMTask(
        task_id=None, type_="SECURITY-GROUP", region=security_group.region, action="DELETE",
        cloud_id=security_group.ibm_cloud.id, resource_id=security_group.id)

    doosradb.session.add(task)
    security_group.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_security_group_workflow.delay(task_id=task.id, cloud_id=security_group.ibm_cloud.id,
                                                  region=security_group.region, security_group_id=security_group.id)

    current_app.logger.info(SECURITY_GROUP_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_security_groups.route('/security-groups/<security_group_id>/rules', methods=['POST'])
@validate_json(ibm_create_security_rule_rule_schema)
@authenticate
def add_ibm_security_group_rule(user_id, user, security_group_id):
    """
    Add IBM Security Group Rule
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param security_group_id: ID for this request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_security_group_rule

    data = request.get_json(force=True)
    security_group = doosradb.session.query(IBMSecurityGroup).filter_by(
        id=security_group_id, cloud_id=data['cloud_id']).first()
    if not security_group:
        return Response("SECURITY_GROUP_NOT_FOUND", status=404)

    cloud = doosradb.session.query(IBMCloud).filter_by(
        id=security_group.ibm_cloud.id, project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_create_ibm_security_group_rule.delay(security_group_id, data, user_id, user.project.id).id, "SECURITY-GROUP-RULE",
        "ADD", cloud.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(SECURITY_GROUP_RULE_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_security_groups.route('/security-groups/<security_group_id>/rules/<rule_id>', methods=['DELETE'])
@authenticate
def delete_ibm_security_group_rule(user_id, user, security_group_id, rule_id):
    """
    Delete an IBM Security Group Rule
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: vpc_id for IBM subnet
    :param subnet_id: subnet_id for IBM subnet
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.security_group_tasks import task_delete_ibm_security_group_rule_workflow

    security_group_rule = doosradb.session.query(IBMSecurityGroupRule).filter_by(
        id=rule_id, security_group_id=security_group_id).first()
    if not security_group_rule:
        current_app.logger.info("No IBM Security Group found with ID {id}".format(id=rule_id))
        return Response(status=404)

    if security_group_rule.security_group.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not security_group_rule.security_group.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="SECURITY-GROUP-RULE", region=security_group_rule.security_group.region, action="DELETE",
        cloud_id=security_group_rule.security_group.ibm_cloud.id, resource_id=security_group_rule.id)

    doosradb.session.add(task)
    security_group_rule.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_security_group_rule_workflow.delay(task_id=task.id,
                                                       cloud_id=security_group_rule.security_group.ibm_cloud.id,
                                                       region=security_group_rule.security_group.region,
                                                       security_group_rule_id=security_group_rule.id)

    current_app.logger.info(SECURITY_GROUP_RULE_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
