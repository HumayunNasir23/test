from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, DELETING, ERROR_CREATING, ERROR_DELETING
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMPublicGateway, IBMVpcNetwork, IBMResourceGroup


def configure_public_gateway(name, vpc_id, data):
    """
    This request creates a new public gateway from a public gateway template.
    """
    ibm_public_gateway = None
    ibm_vpc = IBMVpcNetwork.query.get(vpc_id)
    if not ibm_vpc:
        current_app.logger.debug("IBM VPC Network with ID '{id}' not found".format(id=vpc_id))
        return

    current_app.logger.info("Deploying Public Gateway '{name}' on IBM Cloud".format(name=name))
    try:
        ibm_manager = IBMManager(ibm_vpc.ibm_cloud, ibm_vpc.region)
        existing_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
            zone=data['zone'], vpc_name=ibm_vpc.name)
        if existing_public_gateway:
            raise IBMInvalidRequestError(
                "Public Gateway with name '{}' already configured in zone '{}' for VPC '{}'".format(
                    name, data['zone'], ibm_vpc.name))

        existing_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(name)
        if existing_public_gateway:
            raise IBMInvalidRequestError(
                "Public Gateway with name '{}' already configured in zone'{}'".format(name, data['zone']))

        ibm_public_gateway = IBMPublicGateway(name=name, zone=data['zone'], region=ibm_vpc.region)
        ibm_public_gateway.ibm_cloud = ibm_vpc.ibm_cloud
        ibm_public_gateway.ibm_vpc_network = ibm_vpc

        ibm_resource_group = IBMResourceGroup(name=data["resource_group"], cloud_id=ibm_vpc.ibm_cloud.id)
        ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
        ibm_public_gateway.ibm_resource_group = ibm_resource_group

        doosradb.session.add(ibm_public_gateway)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_public_gateway(ibm_public_gateway)
        configured_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
            name=ibm_public_gateway.name, zone=ibm_public_gateway.zone, vpc_name=ibm_vpc.name)

        if configured_public_gateway:
            configured_public_gateway = configured_public_gateway[0]
            ibm_public_gateway.resource_id = configured_public_gateway.resource_id
            floating_ip_copy = configured_public_gateway.floating_ip.make_copy()
            floating_ip_copy.ibm_cloud = ibm_public_gateway.ibm_cloud
            ibm_public_gateway.floating_ip = floating_ip_copy
            doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_vpc.ibm_cloud.status = INVALID
        if ibm_public_gateway:
            ibm_public_gateway.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_public_gateway.status = CREATED
        doosradb.session.commit()

    return ibm_public_gateway


def delete_public_gateway(public_gateway):
    """
    This request deletes a public gateway. This operation cannot be reversed.
    For this request to succeed, the public gateway must not be attached to any subnets.
    :return:
    """
    current_app.logger.info("Deleting Public Gateway '{name}' on IBM Cloud".format(name=public_gateway.name))
    try:
        ibm_manager = IBMManager(public_gateway.ibm_cloud, public_gateway.ibm_vpc_network.region)
        existing_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
            public_gateway.name, public_gateway.zone, public_gateway.ibm_vpc_network.name)
        if existing_public_gateway:
            public_gateway.status = DELETING
            doosradb.session.commit()
            ibm_manager.rias_ops.delete_public_gateway(existing_public_gateway[0])
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            public_gateway.cloud.status = INVALID
        public_gateway.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        public_gateway.status = DELETED
        doosradb.session.delete(public_gateway)
        doosradb.session.commit()
        return True
