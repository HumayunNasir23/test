import logging

from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, CREATING, ERROR_CREATING, ERROR_UPDATING
from doosra.common.consts import ERROR_DELETING, DELETED
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers import IBMManager
from doosra.ibm.managers.exceptions import *
from doosra.models import IBMCloud
from doosra.models import IBMResourceGroup, IBMVpcNetwork, TransitGateway, TransitGatewayConnection
from doosra.transit_gateway.manager.operations.consts import *

LOGGER = logging.getLogger(__name__)


def configure_transit_gateway(name, cloud_id, data):
    """
    This request creates a new Transit Gateway from a Transit Gateway template.
    """
    transit_gateway = None

    cloud = IBMCloud.query.get(cloud_id)
    if not cloud:
        current_app.logger.info("No IBM cloud found with ID {id}".format(id=data['cloud_id']))
        return

    current_app.logger.info("Deploying Transit Gateway '{name}' on IBM Cloud".format(name=name))
    try:
        ibm_manager = IBMManager(cloud, initialize_tg_manager=True, initialize_rias_ops=False)
        existing_resource_group = ibm_manager.tg_manager.fetch_ops.get_resource_groups(data['resource_group'])

        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))

        transit_gateways = ibm_manager.tg_manager.fetch_ops.get_all_transit_gateways()

        existing_transit_gateway = list(map(lambda obj: obj.name, transit_gateways))
        if data['name'] in existing_transit_gateway:
            raise IBMInvalidRequestError(
                "Transit Gateway with name '{}' already configured for Cloud '{}'".format(name, cloud.name))

        resource_group = doosradb.session.query(IBMResourceGroup).filter_by(
            name=data['resource_group'], cloud_id=cloud_id).first()

        if not resource_group:
            resource_group = existing_resource_group[0]
            resource_group.ibm_cloud = cloud
            doosradb.session.add(resource_group)

        transit_gateway = TransitGateway(
            name=data['name'],
            region=data["location"],
            is_global_route=data["is_global_route"]
        )
        transit_gateway.ibm_cloud = cloud
        transit_gateway.ibm_resource_group = resource_group
        doosradb.session.add(transit_gateway)
        doosradb.session.commit()

        configured_transit_gateway = ibm_manager.tg_manager.push_ops.create_transit_gateway(
            transit_gateway_obj=transit_gateway)

        if not configured_transit_gateway:
            raise IBMInvalidRequestError(
                "Failed to configure Transit Gateway {transit_gateway} on region {region}".format(
                    transit_gateway=transit_gateway.name, region=transit_gateway.region))

        if configured_transit_gateway["name"] == transit_gateway.name:
            transit_gateway.resource_id = configured_transit_gateway["id"]
            transit_gateway.created_at = configured_transit_gateway["created_at"]
            transit_gateway.crn = configured_transit_gateway["crn"]
            transit_gateway.gateway_status = configured_transit_gateway["status"]
            doosradb.session.commit()

        connections = data.get('connections', [])
        # Transit Gateway Connection Creation
        if len(connections):
            for connection in connections:
                existing_transit_gateway_connection = doosradb.session.query(TransitGatewayConnection).filter_by(
                    name=connection['name'], transit_gateway_id=transit_gateway.id).first()

                if existing_transit_gateway_connection:
                    raise IBMInvalidRequestError(
                        "Transit Gateway Connection with name '{}' already configured for TransitGateway '{}'".format(
                            connection['name'], transit_gateway.name))

                configure_transit_gateway_connection(connection['name'], transit_gateway.id, cloud_id, connection)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            cloud.status = INVALID
        if transit_gateway:
            transit_gateway.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        transit_gateway.status = CREATED
        doosradb.session.commit()

    return transit_gateway


def configure_transit_gateway_connection(name, transit_gateway_id, cloud_id, data):
    """
    This request creates a new Transit Gateway Connection from a Transit Gateway Connection template.
    """
    transit_gateway_connection = None
    cloud = IBMCloud.query.get(cloud_id)
    if not cloud:
        current_app.logger.debug("IBM Cloud with ID '{id}' not found".format(id=cloud_id))
        return

    if data.get('vpc_id'):
        vpc = IBMVpcNetwork.query.get(data["vpc_id"])
        if not vpc:
            current_app.logger.debug("IBM VPC Network with ID '{id}' not found".format(id=data['vpc_id']))
            return

    transit_gateway = TransitGateway.query.get(transit_gateway_id)
    if not transit_gateway:
        current_app.logger.debug("Transit Gateway with ID '{id}' not found".format(id=data['transit_gateway_id']))
        return

    current_app.logger.info("Creating Transit Gateway Connection '{}' on IBM Cloud".format(name))
    try:
        ibm_manager = IBMManager(transit_gateway.ibm_cloud, initialize_tg_manager=True, initialize_rias_ops=False)

        existing_transit_gateway = ibm_manager.tg_manager.fetch_ops.get_transit_gateway(transit_gateway.resource_id)
        if not existing_transit_gateway:
            raise IBMInvalidRequestError("Transit Gateway with '{}' not found".format(transit_gateway.name))

        existing_transit_gateway_connections = ibm_manager.tg_manager.fetch_ops.get_all_transit_gateway_connections(
            name=data['name'], transit_gateway_id=existing_transit_gateway.resource_id)
        if existing_transit_gateway_connections:
            raise IBMInvalidRequestError(
                "Connection already exists with name '{}' for Transit Gateway '{}'".format(name, transit_gateway.name))

        transit_gateway_connection = TransitGatewayConnection(
            name=data['name'],
            network_type=data['network_type'],
            network_id=vpc.crn if data['network_type'] == "vpc" else None,
            region=vpc.region if data['network_type'] == "vpc" else None
        )
        transit_gateway_connection.ibm_vpc_network = vpc if data['network_type'] == "vpc" else None
        transit_gateway_connection.transit_gateway = transit_gateway
        doosradb.session.add(transit_gateway_connection)
        doosradb.session.commit()

        configured_transit_gateway_connection = ibm_manager.tg_manager.push_ops.create_transit_gateway_connection(
            connection_obj=transit_gateway_connection, transit_gateway_obj=existing_transit_gateway)

        if not configured_transit_gateway_connection:
            raise IBMInvalidRequestError(
                "Failed to configure Transit Gateway Connection with name {}".format(data['name']))

        transit_gateway_connection.resource_id = configured_transit_gateway_connection["id"]
        transit_gateway_connection.created_at = configured_transit_gateway_connection["created_at"]
        transit_gateway_connection.connection_status = configured_transit_gateway_connection["status"]

        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            cloud.status = INVALID
        if transit_gateway_connection:
            transit_gateway_connection.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        transit_gateway_connection.status = CREATED
        doosradb.session.commit()

    return transit_gateway_connection


def update_transit_gateway(transit_gateway):
    if not transit_gateway:
        return

    current_app.logger.info(f"Updating Transit Gateway '{transit_gateway.name}' on IBM Cloud")

    try:
        ibm_manager = IBMManager(transit_gateway.ibm_cloud, initialize_tg_manager=True, initialize_rias_ops=False)

        tg_exists = ibm_manager.tg_manager.fetch_ops.get_transit_gateway(transit_gateway.resource_id)

        if not tg_exists:
            return

        ibm_manager.tg_manager.push_ops.update_transit_gateway(transit_gateway)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            transit_gateway.cloud.status = INVALID
        transit_gateway.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        transit_gateway.status = CREATED
        doosradb.session.commit()
        return True


def update_transit_gateway_connection(tg_connection):
    if not tg_connection:
        return

    current_app.logger.info(f"Updating Transit Gateway Connection '{tg_connection.name}' on IBM Cloud")

    try:
        ibm_manager = IBMManager(tg_connection.transit_gateway.ibm_cloud, initialize_tg_manager=True,
                                 initialize_rias_ops=False)

        tg_connection_exists = ibm_manager.tg_manager.fetch_ops.get_transit_gateway_connection(tg_connection)

        if not tg_connection_exists:
            return

        ibm_manager.tg_manager.push_ops.update_transit_gateway_connection(tg_connection)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            tg_connection.cloud.status = INVALID
        tg_connection.status = ERROR_UPDATING
        doosradb.session.commit()
    else:
        tg_connection.status = CREATED
        doosradb.session.commit()
        return True


def delete_transit_gateway(transit_gateway):
    if not transit_gateway:
        return

    current_app.logger.info(f"Deleting Transit Gateway '{transit_gateway.name}' on IBM Cloud")

    try:
        ibm_manager = IBMManager(transit_gateway.ibm_cloud, initialize_tg_manager=True, initialize_rias_ops=False)

        tg_exists = ibm_manager.tg_manager.fetch_ops.get_transit_gateway(transit_gateway.resource_id)

        if not tg_exists:
            doosradb.session.delete(transit_gateway)
            doosradb.session.commit()

        for tg_connection in transit_gateway.connections.all():
            delete_transit_gateway_connection(tg_connection)

        ibm_manager.tg_manager.push_ops.delete_transit_gateway(transit_gateway)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            transit_gateway.cloud.status = INVALID
        transit_gateway.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        transit_gateway.status = DELETED
        doosradb.session.delete(transit_gateway)
        doosradb.session.commit()
        return True


def delete_transit_gateway_connection(tg_connection):
    if not tg_connection:
        return

    current_app.logger.info(f"Deleting Transit Gateway Connection '{tg_connection.name}' on IBM Cloud")

    try:
        ibm_manager = IBMManager(tg_connection.transit_gateway.ibm_cloud, initialize_tg_manager=True,
                                 initialize_rias_ops=False)

        tg_connection_exists = ibm_manager.tg_manager.fetch_ops.get_transit_gateway_connection(tg_connection)

        if not tg_connection_exists:
            doosradb.session.delete(tg_connection)
            doosradb.session.commit()

        ibm_manager.tg_manager.push_ops.delete_transit_gateway_connection(tg_connection)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            tg_connection.cloud.status = INVALID
        tg_connection.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        tg_connection.status = DELETED
        doosradb.session.delete(tg_connection)
        doosradb.session.commit()
        return True
