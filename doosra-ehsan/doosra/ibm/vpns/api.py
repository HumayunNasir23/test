from flask import current_app, jsonify, Response, request, json

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.ibm.vpns import ibm_vpns
from doosra.ibm.vpns.consts import *
from doosra.ibm.vpns.schemas import *
from doosra.models import IBMCloud, IBMTask, IBMVpcNetwork, IBMIKEPolicy, IBMIPSecPolicy, \
    IBMVpnGateway, IBMVpnConnection
from doosra.validate_json import validate_json


@ibm_vpns.route('/ike_policies', methods=['POST'])
@validate_json(ibm_ike_policy_schema)
@authenticate
def add_ibm_ike_policy(user_id, user):
    """
    Add IBM IKE Policy
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_ike_policy

    data = request.get_json(force=True)
    # Below are the optional fields: we should use default Resource Group if not provided: PayLoad remains the same
    data['resource_group'] = data.get('resource_group', 'default')
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    ike_policy = doosradb.session.query(IBMIKEPolicy).filter_by(
        name=data['name'], cloud_id=data['cloud_id'], region=data.get('region')).first()
    if ike_policy:
        return Response("ERROR_CONFLICTING_IKE_POLICY_NAME", status=409)

    task = IBMTask(
        task_create_ibm_ike_policy.delay(data.get("name"), cloud.id, data, user_id, user.project.id).id, "IKE-POLICY", "ADD", cloud.id,
        request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(IKE_POLICY_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpns.route('/ike_policies/<ike_policy_id>', methods=['GET'])
@authenticate
def get_ibm_ike_policy(user_id, user, ike_policy_id):
    """
    Get IBM IKE Policy
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param ike_policy_id: ike_policy_id for IKE Policy
    :return: Response object from flask package
    """
    ike_policy = doosradb.session.query(IBMIKEPolicy).filter_by(id=ike_policy_id).first()
    if not ike_policy:
        current_app.logger.info("No IKE Policy found with ID {ike_policy}".format(ike_policy=ike_policy_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=ike_policy.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=ike_policy.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return jsonify(ike_policy.to_json())


@ibm_vpns.route('/ike_policies/<ike_policy_id>', methods=['DELETE'])
@authenticate
def delete_ibm_ike_policy(user_id, user, ike_policy_id):
    """
    Delete an IBM IKE Policy
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param ike_policy_id for IKE Policy
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.vpn_tasks import task_delete_ibm_ike_policy_workflow

    ike_policy = doosradb.session.query(IBMIKEPolicy).filter_by(id=ike_policy_id).first()
    if not ike_policy:
        current_app.logger.info("No IBM IKE Policy found with ID {id}".format(id=ike_policy_id))
        return Response(status=404)

    if not ike_policy.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if ike_policy.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="IKE-POLICY", region=ike_policy.region, action="DELETE",
        cloud_id=ike_policy.ibm_cloud.id, resource_id=ike_policy.id)

    doosradb.session.add(task)
    ike_policy.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_ike_policy_workflow.delay(task_id=task.id, cloud_id=ike_policy.ibm_cloud.id,
                                              region=ike_policy.region, ike_policy_id=ike_policy.id)

    current_app.logger.info(IKE_POLICY_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpns.route('/ike_policies', methods=['GET'])
@authenticate
def list_ibm_ike_policies(user_id, user):
    """
    List all IBM IKE Policies
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    ike_policy_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        ike_polices = ibm_cloud.ike_policies.all()
        for ike in ike_polices:
            ike_policy_list.append(ike.to_json())

    if not ike_policy_list:
        return Response(status=204)

    return jsonify(ike_policy_list)


@ibm_vpns.route('/ipsec_policies', methods=['POST'])
@validate_json(ibm_ipsec_policy_schema)
@authenticate
def add_ibm_ipsec_policy(user_id, user):
    """
    Add IBM IPSec Policy
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """

    from doosra.tasks.other.ibm_tasks import task_create_ibm_ipsec_policy

    data = request.get_json(force=True)
    # Below are the optional fields: we should use default Resource Group if not provided: PayLoad remains the same
    data['resource_group'] = data.get('resource_group', 'default')
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    ipsec_policy = doosradb.session.query(IBMIPSecPolicy).filter_by(
        name=data['name'], cloud_id=data['cloud_id'], region=data.get('region')).first()
    if ipsec_policy:
        return Response("ERROR_CONFLICTING_IPSEC_POLICY_NAME", status=409)

    task = IBMTask(
        task_create_ibm_ipsec_policy.delay(data.get("name"), cloud.id, data, user_id, user.project.id).id, "IPSEC-POLICY", "ADD", cloud.id,
        request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(IPSEC_POLICY_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpns.route('/ipsec_policies/<ipsec_policy_id>', methods=['GET'])
@authenticate
def get_ibm_ipsec_policy(user_id, user, ipsec_policy_id):
    """
    Get IBM Vpc network
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpc_id: vpc_id for VPC network
    :return: Response object from flask package
    """
    ipsec_policy = doosradb.session.query(IBMIPSecPolicy).filter_by(id=ipsec_policy_id).first()
    if not ipsec_policy:
        current_app.logger.info("No IPSec Policy found with ID {ipsec_policy}".format(ipsec_policy=ipsec_policy))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=ipsec_policy.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=ipsec_policy.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return jsonify(ipsec_policy.to_json())


@ibm_vpns.route('/ipsec_policies/<ipsec_policy_id>', methods=['DELETE'])
@authenticate
def delete_ibm_ipsec_policy(user_id, user, ipsec_policy_id):
    """
    Delete an IBM IPSEC Policy
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param ipsec_policy_id for IPSEC Policy
    :return: Response object from flask package
    """

    from doosra.tasks.ibm.vpn_tasks import task_delete_ibm_ipsec_policy_workflow

    ipsec_policy = doosradb.session.query(IBMIPSecPolicy).filter_by(id=ipsec_policy_id).first()
    if not ipsec_policy:
        current_app.logger.info("No IBM IPSEC Policy found with ID {id}".format(id=ipsec_policy_id))
        return Response(status=404)

    if not ipsec_policy.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if ipsec_policy.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="IPSEC-POLICY", region=ipsec_policy.region, action="DELETE",
        cloud_id=ipsec_policy.ibm_cloud.id, resource_id=ipsec_policy.id)

    doosradb.session.add(task)
    ipsec_policy.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_ipsec_policy_workflow.delay(task_id=task.id, cloud_id=ipsec_policy.ibm_cloud.id,
                                                region=ipsec_policy.region, ipsec_policy_id=ipsec_policy.id)

    current_app.logger.info(IPSEC_POLICY_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpns.route('/ipsec_policies', methods=['GET'])
@authenticate
def list_ibm_ipsec_policies(user_id, user):
    """
    List all IBM IPSec Policies
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    ipsec_policy_list = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        ipsec_polices = ibm_cloud.ipsec_policies.all()
        for ike in ipsec_polices:
            ipsec_policy_list.append(ike.to_json())

    if not ipsec_policy_list:
        return Response(status=204)

    return json.dumps(ipsec_policy_list)


@ibm_vpns.route('/vpn_gateways', methods=['POST'])
@validate_json(ibm_vpn_gateway_schema)
@authenticate
def add_ibm_vpn_gateway(user_id, user):
    """
    Add IBM VPN Gateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_vpn_gateway

    data = request.get_json(force=True)
    data['resource_group'] = data.get('resource_group', 'default')
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

    vpn_gateway = doosradb.session.query(IBMVpnGateway).filter_by(
        name=data['name'], cloud_id=data['cloud_id'], region=vpc.region).first()
    if vpn_gateway:
        return Response("ERROR_CONFLICTING_VPN_GATEWAY_NAME", status=409)

    task = IBMTask(
        task_create_ibm_vpn_gateway.delay(data.get("name"), vpc.id, data, user_id, user.project.id).id, "VPN-GATEWAY", "ADD", cloud.id,
        request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(VPN_GATEWAY_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpns.route('/vpn_gateways/<vpn_gateway_id>', methods=['GET'])
@authenticate
def get_ibm_vpn_gateway(user_id, user, vpn_gateway_id):
    """
    Get IBM VPN Gateway
    :param vpn_gateway_id: VPN Gateway ID
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    vpn_gateway = doosradb.session.query(IBMVpnGateway).filter_by(id=vpn_gateway_id).first()
    if not vpn_gateway:
        current_app.logger.info("No IPSec Policy found with ID {vpn_gateway_id}".format(vpn_gateway_id=vpn_gateway_id))
        return Response(status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=vpn_gateway.cloud_id, project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info("No IBM Cloud account found with ID {cloud_id}".format(cloud_id=vpn_gateway.cloud_id))
        return Response(status=404)

    if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    return jsonify(vpn_gateway.to_json())


@ibm_vpns.route('/vpn_gateways/<vpn_gateway_id>', methods=['DELETE'])
@authenticate
def delete_ibm_vpn_gateway(user_id, user, vpn_gateway_id):
    """
    Delete an IBM VPN Gateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpn_gateway_id: vpn_gateway_id for VPN Gateway
    :return: Response object from flask package
    """
    from doosra.tasks.ibm.vpn_tasks import task_delete_ibm_vpn_gateway_workflow

    vpn_gateway = doosradb.session.query(IBMVpnGateway).filter_by(id=vpn_gateway_id).first()
    if not vpn_gateway:
        current_app.logger.info("No IBM VPN Gateway found with ID {id}".format(id=vpn_gateway_id))
        return Response(status=404)

    if not vpn_gateway.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if vpn_gateway.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="VPN-GATEWAY", region=vpn_gateway.region, action="DELETE",
        cloud_id=vpn_gateway.ibm_cloud.id, resource_id=vpn_gateway.id)

    doosradb.session.add(task)
    vpn_gateway.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_vpn_gateway_workflow.delay(task_id=task.id, cloud_id=vpn_gateway.ibm_cloud.id,
                                               region=vpn_gateway.region, vpn_id=vpn_gateway.id)

    current_app.logger.info(VPN_GATEWAY_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpns.route('/vpn_gateways', methods=['GET'])
@authenticate
def list_ibm_vpn_gateways(user_id, user):
    """
    List all IBM VPN Gateways
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    ibm_vpn_gateways = list()
    for ibm_cloud in ibm_cloud_accounts:
        if ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
            continue

        vpn_gateways = ibm_cloud.vpn_gateways.all()
        for vpn_gateway in vpn_gateways:
            ibm_vpn_gateways.append(vpn_gateway.to_json())

    if not ibm_vpn_gateways:
        return Response(status=204)

    return jsonify(ibm_vpn_gateways)


@ibm_vpns.route('/vpn_gateways/<vpn_gateway_id>/connections', methods=['POST'])
@validate_json(ibm_vpn_connection_schema)
@authenticate
def add_ibm_vpn_connection(user_id, user, vpn_gateway_id):
    """
    :param user_id:
    :param user:
    :param vpn_gateway_id:
    """
    from doosra.tasks.other.ibm_tasks import task_create_ibm_vpn_connection

    data = request.get_json(force=True)
    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response(status=404)

    if cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    vpn_gateway_connection = doosradb.session.query(IBMVpnConnection).filter_by(
        name=data['name'], vpn_gateway_id=vpn_gateway_id).first()
    if vpn_gateway_connection:
        return Response("ERROR_CONFLICTING_CONNECTION_NAME", status=409)

    task = IBMTask(
        task_create_ibm_vpn_connection.delay(data.get("name"), cloud.id, data, user_id, user.project.id).id, "VPN-CONNECTION", "ADD",
        cloud.id, request_payload=json.dumps(data))
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(VPN_CONNECTION_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@ibm_vpns.route('/vpn_gateways/<vpn_gateway_id>/connections', methods=['GET'])
@authenticate
def list_ibm_vpn_gateway_connections(user_id, user, vpn_gateway_id):
    """
    List all Connections for a Specific IBM VPN Gateway
    :param vpn_gateway_id: ID of the VPN Gateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_vpn_gateway = doosradb.session.query(IBMVpnGateway).filter_by(id=vpn_gateway_id).first()
    if not ibm_vpn_gateway:
        current_app.logger.info("No VPN Gateway with ID `{}` found. Please create one.".format(vpn_gateway_id))
        return Response(status=404)

    if ibm_vpn_gateway.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    ibm_vpn_connections = list()
    for connection in ibm_vpn_gateway.vpn_connections.all():
        ibm_vpn_connections.append(connection.to_json())

    if not ibm_vpn_connections:
        return Response(status=204)

    return jsonify(ibm_vpn_connections)


@ibm_vpns.route('/vpn_gateways/<vpn_gateway_id>/connections/<connection_id>', methods=['DELETE'])
@authenticate
def delete_ibm_vpn_connection(user_id, user, vpn_gateway_id, connection_id):
    """
    Delete an IBM VPN Gateway Connection
    :param connection_id: ID of the Connection
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :param vpn_gateway_id: vpn_gateway_id for VPN Gateway
    :return: Response object from flask package
    """

    from doosra.tasks.ibm.vpn_tasks import task_delete_ibm_vpn_connection_workflow

    vpn_gateway = IBMVpnGateway.query.get(vpn_gateway_id)
    vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(id=connection_id).first()

    if not vpn_gateway:
        current_app.logger.info(
            "No IBM VPN Gateway found with ID {name}".format(name=vpn_gateway.name))
    if not vpn_connection:
        current_app.logger.info(
            "No IBM VPN Connection found with ID {id} for VPN Gateway {name}".format(id=connection_id,
                                                                                     name=vpn_gateway.name))
        return Response(status=404)

    if not vpn_gateway.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    if vpn_gateway.ibm_cloud.status == IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS:
        return Response(IBMCloud.STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS, status=400)

    task = IBMTask(
        task_id=None, type_="VPN-CONNECTION", region=vpn_connection.region, action="DELETE",
        cloud_id=vpn_connection.ibm_cloud.id, resource_id=vpn_connection.id)

    doosradb.session.add(task)
    vpn_connection.status = DELETING
    doosradb.session.commit()

    task_delete_ibm_vpn_connection_workflow.delay(task_id=task.id, cloud_id=vpn_connection.ibm_cloud.id,
                                                  region=vpn_connection.region,
                                                  vpn_connection_id=vpn_connection.id)

    current_app.logger.info(VPN_CONNECTION_DELETE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
