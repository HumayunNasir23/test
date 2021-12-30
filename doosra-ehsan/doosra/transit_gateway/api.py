from flask import current_app, jsonify, Response, request

from doosra import db as doosradb
from doosra.auth import authenticate
from doosra.common.consts import *
from doosra.models import IBMCloud, IBMTask, TransitGateway, TransitGatewayConnection, IBMVpcNetwork
from doosra.transit_gateway import transit_gateway
from doosra.transit_gateway.schemas import update_transit_gateway_schema, update_tg_connection_schema, \
    transit_gateway_connection_schema, transit_gateway_schema
from doosra.validate_json import validate_json


@transit_gateway.route('/transit_gateways', methods=['POST'])
@validate_json(transit_gateway_schema)
@authenticate
def add_transit_gateway(user_id, user):
    """
    Add TransitGateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    from doosra.tasks.other.transit_gateway_tasks import task_create_transit_gateway

    data = request.get_json(force=True)

    data['resource_group'] = data.get('resource_group', 'default')

    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response("No IBM cloud found with ID {id}".format(id=data['cloud_id']), status=404)

    transit_gateways = doosradb.session.query(TransitGateway).filter_by(cloud_id=data["cloud_id"],
                                                                        region=data['location']).all()
    if len(transit_gateways) >= 2:
        return Response("Maximum Limit of '2' reached for Transit Gateways in this region", status=409)

    transit_gateway = doosradb.session.query(TransitGateway).filter_by(
        name=data['name'], cloud_id=data['cloud_id'], region=data['location']).first()
    if transit_gateway:
        return Response("ERROR_CONFLICTING_TRANSIT_GATEWAY_NAME", status=409)

    task = IBMTask(
        task_create_transit_gateway.delay(data.get("name"), cloud.id, data).id, "TRANSIT-GATEWAY", "ADD", cloud.id,
        request_payload=data)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(TRANSIT_GATEWAY_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@transit_gateway.route('/transit_gateways/<transit_gateway_id>/connections', methods=['POST'])
@validate_json(transit_gateway_connection_schema)
@authenticate
def add_transit_gateway_connection(user_id, user, transit_gateway_id):
    """
    :param user_id:
    :param user:
    :param transit_gateway_id:
    """
    from doosra.tasks.other.transit_gateway_tasks import task_create_transit_gateway_connection

    data = request.get_json(force=True)

    cloud = doosradb.session.query(IBMCloud).filter_by(id=data["cloud_id"], project_id=user.project.id).first()
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return Response("No IBM cloud found with ID {id}".format(id=data['cloud_id']), status=404)

    transit_gateway = doosradb.session.query(TransitGateway).get(transit_gateway_id)
    if not transit_gateway:
        current_app.logger.info(f"Transit Gateway with id `{transit_gateway_id}` not found!")
        return Response(f"Transit Gateway with id `{transit_gateway_id}` not found!", status=409)

    if data["network_type"] == "vpc":
        vpc = doosradb.session.query(IBMVpcNetwork).filter_by(id=data["vpc_id"]).first()
        if not vpc:
            current_app.logger.info("No IBM VPC Network found with ID {id}".format(id=data['vpc_id']))
            return Response("No IBM VPC Network found with ID {id}".format(id=data['vpc_id']), status=404)

        vpc_connection = doosradb.session.query(TransitGatewayConnection).filter_by(network_id=vpc.crn).first()
        if vpc_connection:
            current_app.logger.info(f"Provided VPC `{vpc.name}` is already connected with Transit Gateway")
            return Response(
                f"Provided VPC `{vpc.name}` is already attached to one of the Transit Gateway",
                status=409)

    else:
        transit_gateway_connections = doosradb.session.query(TransitGatewayConnection).filter_by(
            transit_gateway_id=transit_gateway_id, network_type=data["network_type"]).all()
        if len(transit_gateway_connections) >= 1:
            return Response("Classic Connection is already connected with cloud {id}".format(id=data["cloud_id"]), status=409)

    transit_gateway_connection = doosradb.session.query(TransitGatewayConnection).filter_by(
        name=data['name'], transit_gateway_id=transit_gateway_id).first()
    if transit_gateway_connection:
        return Response("ERROR_CONFLICTING_CONNECTION_NAME", status=409)

    task = IBMTask(
        task_create_transit_gateway_connection.delay(data.get("name"), transit_gateway_id, cloud.id, data).id,
        "TRANSIT-GATEWAY-CONNECTION", "ADD",
        cloud.id, request_payload=data)
    doosradb.session.add(task)
    doosradb.session.commit()

    current_app.logger.info(TRANSIT_GATEWAY_CONNECTION_CREATE.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@transit_gateway.route('/transit_gateways', methods=['GET'])
@authenticate
def list_transit_gateways(user_id, user):
    """
    List all Transit Gateways
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=204)

    ibm_transit_gateways = list()
    for ibm_cloud in ibm_cloud_accounts:
        transit_gateways = ibm_cloud.transit_gateways.all()
        for tg in transit_gateways:
            ibm_transit_gateways.append(tg.to_json())

    if not ibm_transit_gateways:
        return Response(status=204)

    return jsonify(ibm_transit_gateways)


@transit_gateway.route('/transit_gateways/<transit_gateway_id>/connections', methods=['GET'])
@authenticate
def list_transit_gateway_connections(user_id, user, transit_gateway_id):
    """
    List all Connections for a Specific Transit Gateway
    :param transit_gateway_id: ID of the Transit Gateway
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=404)

    transit_gateway = doosradb.session.query(TransitGateway).filter_by(id=transit_gateway_id).first()
    if not transit_gateway:
        current_app.logger.info("No Transit Gateway with ID `{}` found. Please create one.".format(transit_gateway_id))
        return Response("No Transit Gateway Found. Please Create One.", status=404)

    transit_gateway_connections = list()
    for connection in transit_gateway.connections.all():
        transit_gateway_connections.append(connection.to_json())

    if not transit_gateway_connections:
        return Response(status=204)

    return jsonify(transit_gateway_connections)


@transit_gateway.route('/transit_gateways/<transit_gateway_id>', methods=['GET'])
@authenticate
def get_transit_gateway(user_id, user, transit_gateway_id):
    """
    Get Transit Gateway
    :param transit_gateway_id: Transit Gateway ID
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    transit_gateway = doosradb.session.query(TransitGateway).filter_by(id=transit_gateway_id).first()
    if not transit_gateway:
        current_app.logger.info(
            "No Transit Gateway found with ID {transit_gateway_id}".format(transit_gateway_id=transit_gateway_id))
        return Response("No Transit Gateway Found. Please Create One.", status=404)

    ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=transit_gateway.cloud_id,
                                                           project_id=user.project.id).first()
    if not ibm_cloud:
        current_app.logger.info(
            "No IBM Cloud account found with ID {cloud_id}".format(cloud_id=transit_gateway.cloud_id))
        return Response(status=404)

    return jsonify(transit_gateway.to_json())


@transit_gateway.route('/transit_gateways/<transit_gateway_id>/connections/<connection_id>', methods=['GET'])
@authenticate
def get_transit_gateway_connection(user_id, user, transit_gateway_id, connection_id):
    """
    List Specific Connections for a Specific Transit Gateway
    :param transit_gateway_id: ID of the Transit Gateway
    :param connection_id: ID of the Transit Gateway Connection
    :param user_id: ID of the user initiating the request
    :param user: object of the user initiating the request
    :return: Response object from flask package
    """
    ibm_cloud_accounts = doosradb.session.query(IBMCloud).filter_by(project_id=user.project.id).all()
    if not ibm_cloud_accounts:
        current_app.logger.info("No IBM Cloud accounts found for project with ID {}".format(user.project.id))
        return Response(status=404)

    transit_gateway = doosradb.session.query(TransitGateway).filter_by(id=transit_gateway_id).first()
    if not transit_gateway:
        current_app.logger.info("No Transit Gateway with ID `{}` found. Please create one.".format(transit_gateway_id))
        return Response(status=404)

    transit_gateway_connection = doosradb.session.query(TransitGatewayConnection).filter_by(id=connection_id).first()
    if not transit_gateway_connection:
        current_app.logger.info(
            "No Transit Gateway Connection with ID `{}` found. Please create one.".format(connection_id))
        return Response("No Transit Gateway Found. Please Create One.", status=404)

    return jsonify(transit_gateway_connection.to_json())


@transit_gateway.route('/transit_gateways/<gateway_id>', methods=['PATCH'])
@validate_json(update_transit_gateway_schema)
@authenticate
def update_transit_gateway(user, user_id, gateway_id):
    """
    Update API Call for Transit Gateway. Only `name` and `is_global_route` can be update.
    :param user:
    :param user_id:
    :param gateway_id:
    """
    from doosra.tasks.other.transit_gateway_tasks import task_update_transit_gateway

    data = request.get_json(force=True)
    transit_gateway = doosradb.session.query(TransitGateway).get(gateway_id)
    if not transit_gateway:
        current_app.logger.info(f"No IBM Transit Gateway found with ID {gateway_id}")
        return Response("No Transit Gateway Found. Please Create One.", status=404)

    if data.get('name') and data["name"] != transit_gateway.name:
        transit_gateway.name = data["name"]

    if "is_global_route" in data.keys():
        transit_gateway.is_global_route = data["is_global_route"]

    doosradb.session.commit()

    task = IBMTask(
        task_update_transit_gateway.delay(gateway_id).id, type_="TRANSIT-GATEWAY",
        region=transit_gateway.region, action="UPDATE",
        cloud_id=transit_gateway.ibm_cloud.id, resource_id=transit_gateway.id)

    doosradb.session.add(task)
    transit_gateway.status = UPDATING
    doosradb.session.commit()

    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@transit_gateway.route('/transit_gateways/<gateway_id>/connections/<connection_id>', methods=['PATCH'])
@validate_json(update_tg_connection_schema)
@authenticate
def update_transit_gateway_connection(user, user_id, gateway_id, connection_id):
    """
    Update API Call for Transit Gateway Connection. Only `name` can be updated.
    :param user:
    :param user_id:
    :param gateway_id:
    """
    from doosra.tasks.other.transit_gateway_tasks import task_update_transit_gateway_connection

    data = request.get_json(force=True)
    transit_gateway = doosradb.session.query(TransitGateway).get(gateway_id)
    if not transit_gateway:
        current_app.logger.info(f"No IBM Transit Gateway found with ID {gateway_id}")
        return Response("No Transit Gateway Found. Please Create One.", status=404)

    tg_connection = doosradb.session.query(TransitGatewayConnection).get(connection_id)
    if not tg_connection:
        current_app.logger.info(f"No IBM Transit Gateway Connection found with ID {connection_id}")
        return Response(status=404)

    if data.get('name') and data["name"] != tg_connection.name:
        tg_connection.name = data["name"]

    doosradb.session.commit()

    task = IBMTask(
        task_id=task_update_transit_gateway_connection.delay(connection_id).id,
        type_="TRANSIT-GATEWAY-CONNECTION", region=transit_gateway.region, action="UPDATE",
        cloud_id=transit_gateway.ibm_cloud.id, resource_id=tg_connection.id)

    doosradb.session.add(task)
    tg_connection.status = UPDATING
    doosradb.session.commit()

    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


from doosra.transit_gateway.consts import *


@transit_gateway.route('/transit_gateways/<gateway_id>', methods=['DELETE'])
@authenticate
def delete_transit_gateway(user, user_id, gateway_id):
    from doosra.tasks.other.transit_gateway_tasks import task_delete_transit_gateway

    transit_gateway = doosradb.session.query(TransitGateway).get(gateway_id)

    if not transit_gateway:
        current_app.logger.info(f"No IBM VPN Gateway found with ID {gateway_id}")
        return Response(status=404)

    if not transit_gateway.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_delete_transit_gateway.delay(transit_gateway.id).id, type_="TRANSIT-GATEWAY", action="DELETE",
        cloud_id=transit_gateway.ibm_cloud.id, resource_id=transit_gateway.id)
    doosradb.session.add(task)
    transit_gateway.status = DELETING
    doosradb.session.commit()

    current_app.logger.info(DELETE_TRANSIT_GATEWAY.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp


@transit_gateway.route('/transit_gateways/<gateway_id>/connections/<connection_id>', methods=['DELETE'])
@authenticate
def delete_transit_gateway_connection(user, user_id, gateway_id, connection_id):
    from doosra.tasks.other.transit_gateway_tasks import task_delete_transit_gateway_connection

    transit_gateway = doosradb.session.query(TransitGateway).get(gateway_id)

    if not transit_gateway:
        current_app.logger.info(f"No IBM Transit Gateway found with ID {gateway_id}")
        return Response("No Transit Gateway Found. Please Create One.", status=404)

    tg_connection = doosradb.session.query(TransitGatewayConnection).get(connection_id)
    if not tg_connection:
        current_app.logger.info(f"No IBM Transit Gateway Connection found with ID {connection_id}")
        return Response("No Transit Gateway Connectoin Found. Please Create One.", status=404)

    if not transit_gateway.ibm_cloud.project_id == user.project.id:
        return Response("INVALID_IBM_CLOUD", status=400)

    task = IBMTask(
        task_id=task_delete_transit_gateway_connection.delay(connection_id=connection_id).id,
        type_="TRANSIT-GATEWAY-CONNECTION", region=transit_gateway.region, action="DELETE",
        cloud_id=transit_gateway.ibm_cloud.id, resource_id=tg_connection.id)

    doosradb.session.add(task)
    tg_connection.status = DELETING
    doosradb.session.commit()

    current_app.logger.info(DELETE_TRANSIT_GATEWAY_CONNECTION.format(user.email))
    resp = jsonify({"task_id": task.id})
    resp.status_code = 202
    return resp
