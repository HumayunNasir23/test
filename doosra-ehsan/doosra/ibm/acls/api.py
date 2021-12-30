import json

from flask import current_app, request, Response, jsonify

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.ibm.acls import ibm_acls
from doosra.ibm.acls.consts import *
from doosra.ibm.acls.schemas import *
from doosra.models import IBMCloud, IBMNetworkAcl, IBMNetworkAclRule, IBMTask
from doosra.validate_json import validate_json


@ibm_acls.route('/acls', methods=['POST'])
@validate_json(ibm_create_acl_schema)
@authenticate
def add_ibm_acl(user_id, user):
    """
    Add an IBM ACL
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_network_acl

    data = request.get_json(force=True)
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    network_acl = doosradb.session.query(IBMNetworkAcl).filter_by(name=data['name'], cloud_id=data['cloud_id'],
                                                                  region=data.get('region')).first()
    if network_acl:
        return Response("ERROR_CONFLICTING_ACL_NAME", status=409)

    task = IBMTask(
        task_create_ibm_network_acl.delay(cloud.id, data.get("name"), data.get("region"), data, user_id,
                                          user.project.id).id, "NETWORK-ACL",
        "ADD", cloud.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(ACL_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_acls.route('/acls/<acl_id>/rules', methods=['POST'])
@validate_json(ibm_create_acl_rule_schema)
@authenticate
def add_ibm_acl_rule(user_id, user, acl_id):
    """
    Add an IBM ACL Rule
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_network_acl_rule

    data = request.get_json(force=True)
    network_acl = doosradb.session.query(IBMNetworkAcl).filter_by(id=acl_id, cloud_id=data['cloud_id']).first()
    if not network_acl:
        return Response("ACL_NOT_FOUND", status=404)

    cloud = doosradb.session.query(IBMCloud).filter_by(id=network_acl.ibm_cloud.id, project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    network_acl_rule = doosradb.session.query(IBMNetworkAclRule).filter_by(name=data['name'], acl_id=acl_id).first()
    if network_acl_rule:
        return Response("ERROR_CONFLICTING_ACL_RULE_NAME", status=409)

    task = IBMTask(
        task_create_ibm_network_acl_rule.delay(data.get("name"), acl_id, data, user_id, user.project.id).id,
        "NETWORK-ACL-RULE",
        "ADD", cloud.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(ACL_RULE_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_acls.route('/acls/<acl_id>', methods=['GET'])
@authenticate
def get_ibm_network_acl(user_id, user, acl_id):
    """
    Get IBM Vpc network
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param acl_id: acl_id
    :return: Response object from flask package
    """
    network_acl = doosradb.session.query(IBMNetworkAcl).filter_by(id=acl_id).first()
    if not network_acl:
        current_app.logger.info("No Network ACL found with ID {acl_id}".format(acl_id=acl_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=network_acl.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=network_acl.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    network_acl_json = network_acl.to_json()
    network_acl_json["subnets"] = [subnet.to_json() for subnet in network_acl.subnets.all()]
    return Response(json.dumps(network_acl_json), mimetype="application/json")


@ibm_acls.route('/acls', methods=['GET'])
@authenticate
def list_ibm_network_acls(user_id, user):
    """
    List all IBM Network ACLs
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    network_acls_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        network_acls = ibm_cloud.network_acls.all()
        for acl in network_acls:
            acl_json = acl.to_json()
            acl_json["subnets"] = [subnet.to_json() for subnet in acl.subnets.all()]
            network_acls_list.append(acl_json)

    if not network_acls_list:
        return Response(status=204)

    return Response(json.dumps(network_acls_list), mimetype='application/json')


@ibm_acls.route('/acls/<acl_id>', methods=['DELETE'])
@authenticate
def delete_ibm_acl(user_id, user, acl_id):
    """
    Delete an IBM Network ACL
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param acl_id: ID for ACL object
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.acl_tasks import task_delete_network_acl_workflow

    network_acl = doosradb.session.query(IBMNetworkAcl).filter_by(id=acl_id).first()
    if not network_acl:
        current_app.logger.info("No IBM Network ACL found with ID {id}".format(id=acl_id))
        return Response(status=404)

    if network_acl.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not network_acl.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if network_acl.is_default:
        return Response("ERROR_DEFAULT_ACL", status=400)

    if network_acl.subnets.all():
        return Response("ERROR_SUBNETS_ATTACHED", status=400)

    task = IBMTask(
        task_id=None, type_="NETWORK-ACL", region=network_acl.region, action="DELETE",
        cloud_id=network_acl.ibm_cloud.id, resource_id=network_acl.id)

    doosradb.session.add(task)
    network_acl.status = DELETING
    doosradb.session.commit()

    task_delete_network_acl_workflow.delay(task_id=task.id, cloud_id=network_acl.ibm_cloud.id,
                                           region=network_acl.region, ibm_network_acl_id=network_acl.id)

    current_app.logger.info(ACL_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_acls.route('/acls/<acl_id>/rules/<acl_rule_id>', methods=['DELETE'])
@authenticate
def delete_ibm_acl_rule(user_id, user, acl_id, acl_rule_id):
    """
    Delete an IBM Network ACL
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param acl_id: ID of ACL object
    :param acl_rule_id: ID for ACL Rule object
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.acl_tasks import task_delete_network_acl_rule_workflow

    network_acl_rule = doosradb.session.query(IBMNetworkAclRule).filter_by(id=acl_rule_id, acl_id=acl_id).first()
    if not network_acl_rule:
        current_app.logger.info("No IBM Network ACL Rule found with ID {id}".format(id=acl_rule_id))
        return Response(status=404)

    if network_acl_rule.ibm_network_acl.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    if not network_acl_rule.ibm_network_acl.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=None, type_="NETWORK-ACL-RULE", region=network_acl_rule.ibm_network_acl.region, action="DELETE",
        cloud_id=network_acl_rule.ibm_network_acl.ibm_cloud.id, resource_id=network_acl_rule.id)

    doosradb.session.add(task)
    network_acl_rule.status = DELETING
    doosradb.session.commit()

    task_delete_network_acl_rule_workflow.delay(task_id=task.id,
                                                cloud_id=network_acl_rule.ibm_network_acl.ibm_cloud.id,
                                                region=network_acl_rule.ibm_network_acl.region,
                                                ibm_network_acl_rule_id=network_acl_rule.id)

    current_app.logger.info(ACL_RULE_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
