from datetime import datetime

from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, ERROR_CREATING, ERROR_DELETING, DELETED
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMIKEPolicy, IBMResourceGroup, IBMIPSecPolicy, IBMVpnGateway, IBMSubnet, \
    IBMCloud, IBMVpnConnection
from doosra.models import IBMVpcNetwork


def configure_ibm_ike_policy(ike_policy_name, cloud_id, data):
    """
    This request creates a new IKE Policy from a IKE Policy template. Each IKE Policy may be
    scoped to one or more VPN connection(s).
    :return:
    """
    ibm_ike_policy = None
    ibm_cloud = IBMCloud.query.get(cloud_id)
    if not ibm_cloud:
        current_app.logger.debug("IBM Cloud {} not found".format(cloud_id))
        return

    current_app.logger.info("Deploying IKE Policy '{name}' on IBM Cloud".format(name=ike_policy_name))
    try:
        ibm_manager = IBMManager(ibm_cloud, region=data['region'])
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])

        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))

        existing_ike_policy = ibm_manager.rias_ops.fetch_ops.get_all_ike_policies(ike_policy_name)
        if existing_ike_policy:
            raise IBMInvalidRequestError(
                "IKE Policy with name '{}' already configured in region '{}'".format(
                    ike_policy_name, data['region']))
        resource_group = doosradb.session.query(IBMResourceGroup).filter_by(
            name=data['resource_group'], cloud_id=ibm_cloud.id).first()
        if not resource_group:
            resource_group = existing_resource_group[0]
            resource_group.ibm_cloud = ibm_cloud
            doosradb.session.add(resource_group)
        ibm_ike_policy = IBMIKEPolicy(
            name=ike_policy_name, region=data['region'], authentication_algorithm=data['authentication_algorithm'],
            encryption_algorithm=data['encryption_algorithm'], key_lifetime=data['key_lifetime'],
            ike_version=data['ike_version'], dh_group=data['dh_group'])
        ibm_ike_policy.ibm_cloud = ibm_cloud
        ibm_ike_policy.ibm_resource_group = resource_group

        ike_policies = ibm_manager.rias_ops.fetch_ops.get_all_ike_policies()
        if len(ike_policies) >= 20:
            raise IBMInvalidRequestError(
                "Maximum Limit of '20' reached for IBM IKE Policies on Account `{name}`".format(
                    name=ibm_cloud.project.name))

        ibm_manager.rias_ops.create_ike_policy(ike_policy_obj=ibm_ike_policy)
        configured_ike_policy = ibm_manager.rias_ops.fetch_ops.get_all_ike_policies(name=ike_policy_name)

        if not configured_ike_policy:
            raise IBMInvalidRequestError("Failed to configure IKE policy....")

        configured_ike_policy = configured_ike_policy[0]
        ibm_ike_policy.resource_id = configured_ike_policy.resource_id
        doosradb.session.add(ibm_ike_policy)
        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
        if ibm_ike_policy:
            ibm_ike_policy.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_ike_policy.status = CREATED

    return ibm_ike_policy


def delete_ibm_ike_policy(ike_policy):
    """
    This request deletes an IKE Policy. This operation cannot be reversed.
    :return:
    """
    current_app.logger.info("Deleting IKE Policy '{name}' on IBM Cloud".format(name=ike_policy.name))
    try:
        ibm_manager = IBMManager(ike_policy.ibm_cloud, ike_policy.region)
        existing_ike_policy = ibm_manager.rias_ops.fetch_ops.get_all_ike_policies(name=ike_policy.name)
        if existing_ike_policy:
            ibm_manager.rias_ops.delete_ike_policy(ike_policy_obj=ike_policy)
            ike_policy.status = DELETED
            doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ike_policy.cloud.status = INVALID
        ike_policy.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ike_policy.status = DELETED
        doosradb.session.delete(ike_policy)
        doosradb.session.commit()
        return True


def configure_ibm_ipsec_policy(ipsec_policy_name, cloud_id, data):
    """
    This request creates a new IP Sec Policy from a IP Sec Policy template. Each IPSec may be
    scoped to one or VPN Connection(s).
    return:
    """
    ibm_ipsec_policy = None
    ibm_cloud = IBMCloud.query.get(cloud_id)
    if not ibm_cloud:
        current_app.logger.debug("IBM Cloud {} not found".format(ibm_cloud))
        return

    current_app.logger.info("Deploying IPsec Policy '{name}' on IBM Cloud".format(name=ipsec_policy_name))
    try:
        ibm_manager = IBMManager(ibm_cloud, region=data['region'])
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])

        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))

        existing_ipsec_policy = ibm_manager.rias_ops.fetch_ops.get_all_ipsec_policies(name=ipsec_policy_name)
        if existing_ipsec_policy:
            raise IBMInvalidRequestError(
                "IPSec Policy with name '{}' already configured in region '{}'".format(
                    ipsec_policy_name, data['region']))
        resource_group = doosradb.session.query(IBMResourceGroup).filter_by(
            name=data['resource_group'], cloud_id=ibm_cloud.id).first()
        if not resource_group:
            resource_group = existing_resource_group[0]
            resource_group.ibm_cloud = ibm_cloud
            doosradb.session.add(resource_group)

        ibm_ipsec_policy = IBMIPSecPolicy(
            ipsec_policy_name, data['region'], authentication_algorithm=data['authentication_algorithm'],
            encryption_algorithm=data['encryption_algorithm'], key_lifetime=data['key_lifetime'],
            pfs_dh_group=data['pfs'])
        ibm_ipsec_policy.ibm_resource_group = resource_group

        ipsec_policies = ibm_manager.rias_ops.fetch_ops.get_all_ipsec_policies()

        if len(ipsec_policies) >= 20:
            raise IBMInvalidRequestError(
                "Maximum Limit of '20' reached for IBM IPSec Policies for Account `{name}`".format(
                    name=ibm_cloud.project.name))

        ibm_manager.rias_ops.create_ipsec_policy(ipsec_policy_obj=ibm_ipsec_policy)
        configured_ipsec_policy = ibm_manager.rias_ops.fetch_ops.get_all_ipsec_policies(name=ipsec_policy_name)

        if not configured_ipsec_policy:
            raise IBMInvalidRequestError("Failed to configure IPSec policy....")

        configured_ipsec_policy = configured_ipsec_policy[0]
        ibm_ipsec_policy.resource_id = configured_ipsec_policy.resource_id
        ibm_ipsec_policy.ibm_cloud = ibm_cloud
        doosradb.session.add(ibm_ipsec_policy)
        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
        if ibm_ipsec_policy:
            ibm_ipsec_policy.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_ipsec_policy.status = CREATED

    return ibm_ipsec_policy


def delete_ibm_ipsec_policy(ipsec_policy):
    """
    This request deletes an IPSec Policy. This operation cannot be reversed.
    :return:
    """
    current_app.logger.info("Deleting IP-SEC Policy '{name}' on IBM Cloud".format(name=ipsec_policy.name))
    try:
        ibm_manager = IBMManager(ipsec_policy.ibm_cloud, ipsec_policy.region)
        existing_ipsec_policy = ibm_manager.rias_ops.fetch_ops.get_all_ipsec_policies(name=ipsec_policy.name)
        if existing_ipsec_policy:
            ibm_manager.rias_ops.delete_ipsec_policy(ipsec_policy_obj=ipsec_policy)
            ipsec_policy.status = DELETED
            doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ipsec_policy.cloud.status = INVALID
        ipsec_policy.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ipsec_policy.status = DELETED
        doosradb.session.delete(ipsec_policy)
        doosradb.session.commit()
        return True


def configure_ibm_vpn_gateway(name, vpc_id, data):
    """
    This request creates a new VPN Gateway from a VPN Gateway template.
    """
    ibm_vpn_gateway = None
    ibm_vpc = IBMVpcNetwork.query.get(vpc_id)

    if not ibm_vpc:
        current_app.logger.debug("IBM VPC Network with ID '{id}' not found".format(id=vpc_id))
        return

    current_app.logger.info("Deploying VPN Gateway '{name}' on IBM Cloud".format(name=name))
    try:
        ibm_manager = IBMManager(ibm_vpc.ibm_cloud, ibm_vpc.region)
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])

        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))

        vpn_gateways = ibm_manager.rias_ops.fetch_ops.get_all_vpn_gateways()
        if len(vpn_gateways) >= 3:
            raise IBMInvalidRequestError(
                "Maximum Limit of '3' reached for IBM VPN Gateways for Region `{name}`".format(
                    name=ibm_vpc.region))

        existing_vpn_gateway = list(map(lambda obj: obj.name, vpn_gateways))
        if data['name'] in existing_vpn_gateway:
            raise IBMInvalidRequestError(
                "VPN Gateway with name '{}' already configured for VPC '{}'".format(name, ibm_vpc.name))

        existing_vpn_subnet = doosradb.session.query(IBMSubnet).filter_by(id=data['subnet'], vpc_id=ibm_vpc.id).first()
        if not existing_vpn_subnet:
            raise IBMInvalidRequestError(
                "Subnet with ID '{}' not configured for VPC '{}'".format(data['subnet'], ibm_vpc.id))

        resource_group = doosradb.session.query(IBMResourceGroup).filter_by(
            name=data['resource_group'], cloud_id=ibm_vpc.ibm_cloud.id).first()

        if not resource_group:
            resource_group = existing_resource_group[0]
            resource_group.ibm_cloud = ibm_vpc.ibm_cloud
            doosradb.session.add(resource_group)

        ibm_vpn_gateway = IBMVpnGateway(name, region=ibm_vpc.region)
        ibm_vpn_gateway.ibm_cloud = ibm_vpc.ibm_cloud
        ibm_vpn_gateway.ibm_vpc_network = ibm_vpc
        ibm_vpn_gateway.ibm_subnet = existing_vpn_subnet
        ibm_vpn_gateway.ibm_resource_group = resource_group
        doosradb.session.add(ibm_vpn_gateway)
        doosradb.session.commit()

        ibm_manager.rias_ops.push_obj_confs(ibm_vpn_gateway)
        configured_vpn_gateway = ibm_manager.rias_ops.fetch_ops.get_all_vpn_gateways(name=ibm_vpn_gateway.name)

        if not configured_vpn_gateway:
            raise IBMInvalidRequestError("Failed to configure VPN Gateway {vpn_gateway} on region {region}".format(
                vpn_gateway=ibm_vpn_gateway.name, region=ibm_vpc.region))

        configured_vpn_gateway = configured_vpn_gateway[0]
        ibm_vpn_gateway.resource_id = configured_vpn_gateway.resource_id
        ibm_vpn_gateway.public_ip = configured_vpn_gateway.public_ip
        ibm_vpn_gateway.gateway_status = configured_vpn_gateway.gateway_status
        ibm_vpn_gateway.created_at = datetime.strptime(configured_vpn_gateway.created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        doosradb.session.commit()

        connections = data.get('connections', [])
        # Vpn Connection Creation
        if len(connections):
            for connection in connections:
                existing_vpn_connection = doosradb.session.query(IBMVpnConnection).filter_by(
                    name=connection['name'], vpn_gateway_id=ibm_vpn_gateway.id).first()

                if existing_vpn_connection:
                    raise IBMInvalidRequestError(
                        "VPN Connection with name '{}' already configured for VpnGateway '{}'".format(
                            connection['name'], ibm_vpn_gateway.name))

                connection['vpn_gateway_id'] = ibm_vpn_gateway.id
                configure_ibm_vpn_connection(connection['name'], ibm_vpc.cloud_id, connection)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_vpc.ibm_cloud.status = INVALID
        if ibm_vpn_gateway:
            ibm_vpn_gateway.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_vpn_gateway.status = CREATED
        doosradb.session.commit()

    return ibm_vpn_gateway


def delete_ibm_vpn_gateway(vpn_gateway):
    """
    This request deletes a VPN Gateway. This operation cannot be reversed.
    :return:
    """
    current_app.logger.info("Deleting VPN Gateway '{name}' on IBM Cloud".format(name=vpn_gateway.name))
    try:
        ibm_manager = IBMManager(vpn_gateway.ibm_cloud, vpn_gateway.region)
        existing_vpn_gateway = ibm_manager.rias_ops.fetch_ops.get_all_vpn_gateways(name=vpn_gateway.name)
        if existing_vpn_gateway:
            ibm_manager.rias_ops.push_obj_confs(existing_vpn_gateway[0], delete=True)
            vpn_gateway.status = DELETED
            doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            vpn_gateway.cloud.status = INVALID
        vpn_gateway.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        vpn_gateway.status = DELETED
        doosradb.session.delete(vpn_gateway)
        doosradb.session.commit()
        return True


def configure_ibm_vpn_connection(name, cloud_id, data):
    """
    This request creates a new VPN Gateway Connection from a VPN Connection template.
    """
    ibm_vpn_connection = None
    ibm_cloud = IBMCloud.query.get(cloud_id)
    if not ibm_cloud:
        current_app.logger.debug("IBM Cloud with ID '{id}' not found".format(id=cloud_id))
        return

    vpn_gateway = IBMVpnGateway.query.get(data['vpn_gateway_id'])
    if not vpn_gateway:
        current_app.logger.debug("IBM VPN Gateway with ID '{id}' not found".format(id=data['vpn_gateway_id']))
        return

    if not data.get('dead_peer_detection'):
        data['dead_peer_detection'] = {
            'action': 'none',
            'timeout': 120,
            'interval': 30
        }

    current_app.logger.info("Creating VPN Connection '{}' on IBM Cloud".format(name))
    try:
        ibm_manager = IBMManager(ibm_cloud, vpn_gateway.region)
        existing_vpn_gateway = ibm_manager.rias_ops.fetch_ops.get_all_vpn_gateways(name=vpn_gateway.name)
        if not existing_vpn_gateway:
            raise IBMInvalidRequestError("VPN Gateway with '{}' not found".format(vpn_gateway.name))

        existing_vpn_connections = ibm_manager.rias_ops.fetch_ops.get_all_vpn_connections(
            name=data['name'], vpn_gateway_id=existing_vpn_gateway[0].resource_id)
        if existing_vpn_connections:
            raise IBMInvalidRequestError(
                "Connection already exists with name '{}' for VPN Gateway '{}'".format(name, vpn_gateway.name))

        ibm_vpn_connection = IBMVpnConnection(
            name=data['name'], dpd_timeout=data['dead_peer_detection'].get('timeout'),
            dpd_interval=data['dead_peer_detection'].get('interval'),
            dpd_action=data['dead_peer_detection'].get('action'), local_cidrs=json.dumps(data['local_cidrs']),
            peer_cidrs=json.dumps(data['peer_cidrs']), peer_address=data['peer_address'],
            pre_shared_key=data['pre_shared_secret'], vpn_gateway_id=data['vpn_gateway_id'])

        if data.get('ipsec_policy_id'):
            ibm_vpn_connection.ibm_ipsec_policy = IBMIPSecPolicy.query.get(data['ipsec_policy_id'])

        if data.get('ike_policy_id'):
            ibm_vpn_connection.ibm_ike_policy = IBMIKEPolicy.query.get(data['ike_policy_id'])

        doosradb.session.add(ibm_vpn_connection)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_vpn_connection(
            connection_obj=ibm_vpn_connection, vpn_gateway_obj=existing_vpn_gateway[0])
        configured_vpn_connection = ibm_manager.rias_ops.fetch_ops.get_all_vpn_connections(
            name=data['name'], vpn_gateway_id=existing_vpn_gateway[0].resource_id)

        if not configured_vpn_connection:
            raise IBMInvalidRequestError("Failed to configure VPN Connection with name {}".format(data['name']))

        configured_vpn_connection = configured_vpn_connection[0]
        ibm_vpn_connection.resource_id = configured_vpn_connection.resource_id
        ibm_vpn_connection.authentication_mode = configured_vpn_connection.authentication_mode
        ibm_vpn_connection.vpn_status = configured_vpn_connection.vpn_status
        ibm_vpn_connection.created_at = datetime.strptime(configured_vpn_connection.created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        ibm_vpn_connection.local_address = vpn_gateway.public_ip
        ibm_vpn_connection.route_mode = configured_vpn_connection.route_mode
        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_cloud.status = INVALID
        if ibm_vpn_connection:
            ibm_vpn_connection.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_vpn_connection.status = CREATED
        doosradb.session.commit()

    return ibm_vpn_connection


def delete_ibm_vpn_connection(vpn_connection, vpn_gateway_id):
    """
    This request deletes an Connection for VPN Gateway. This operation cannot be reversed.
    :return:
    """
    current_app.logger.info("Deleting Connection '{name}' on IBM Cloud".format(name=vpn_connection.name))
    ibm_vpn_gateway = IBMVpnGateway.query.get(vpn_gateway_id)
    try:
        ibm_manager = IBMManager(ibm_vpn_gateway.ibm_cloud, ibm_vpn_gateway.ibm_cloud.vpc_networks[0].region)
        existing_vpn_connection = ibm_manager.rias_ops.fetch_ops.get_all_vpn_connections(name=vpn_connection.name,
                                                                                         vpn_gateway_id=ibm_vpn_gateway.resource_id)
        if existing_vpn_connection:
            ibm_manager.rias_ops.delete_vpn_connection(vpn_connection_obj=vpn_connection,
                                                       vpn_gateway_id=ibm_vpn_gateway.resource_id)
            vpn_connection.status = DELETED
            doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            vpn_connection.cloud.status = INVALID
        vpn_connection.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        vpn_connection.status = DELETED
        doosradb.session.delete(vpn_connection)
        doosradb.session.commit()
        return True
