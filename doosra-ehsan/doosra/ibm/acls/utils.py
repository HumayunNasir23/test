from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMCloud, IBMNetworkAcl, IBMNetworkAclRule, IBMSubnet, IBMResourceGroup


def configure_network_acl(cloud_id, acl_name, region, data):
    """
    This request creates a new network ACL from a network ACL template. The network ACL template
    object is structured in the same way as a retrieved network ACL, and contains the information
    necessary to create the new network ACL
    :return:
    """
    ibm_network_acl, subnets_to_configure = None, list()
    cloud = IBMCloud.query.get(cloud_id)
    if not cloud:
        current_app.logger.debug("IBM Cloud with ID {} not found".format(cloud_id))
        return

    current_app.logger.info("Deploying IBM Network ACL '{name}' on IBM Cloud".format(name=acl_name))
    try:
        ibm_manager = IBMManager(cloud, region)
        existing_network_acl = ibm_manager.rias_ops.fetch_ops.get_all_networks_acls(acl_name)
        if existing_network_acl:
            raise IBMInvalidRequestError(
                "ACL with name '{}' already configured in region '{}'".format(acl_name, region))
        ibm_network_acl = IBMNetworkAcl(acl_name, region)
        ibm_network_acl.cloud_id = cloud_id
        ibm_resource_group = IBMResourceGroup(name=data["resource_group"], cloud_id=cloud_id)
        ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
        ibm_network_acl.ibm_resource_group = ibm_resource_group

        if data.get('rules'):
            for rule in data['rules']:
                ibm_rule = IBMNetworkAclRule(
                    rule['name'], rule['action'], rule.get('destination'), rule['direction'], rule.get('source'),
                    rule['protocol'], rule.get('port_max'), rule.get('port_min'), rule.get('source_port_max'),
                    rule.get('source_port_min'), rule.get('code'), rule.get('type'))
                ibm_network_acl.rules.append(ibm_rule)

        if data.get('subnets'):
            for subnet_id in data['subnets']:
                subnet = doosradb.session.query(IBMSubnet).filter_by(id=subnet_id).first()
                existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(subnet.name, subnet.zone,
                                                                                 subnet.ibm_vpc_network.name)
                if not existing_subnet:
                    raise IBMInvalidRequestError(
                        "Subnet with name '{subnet}' not found in IBM zone '{zone}'".format(
                            subnet=subnet.name, zone=subnet.zone))
                ibm_network_acl.subnets.append(subnet)
                ibm_network_acl.vpc_id = subnet.vpc_id
                doosradb.session.commit()
                subnets_to_configure.append(subnet)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_network_acl(ibm_network_acl)
        configured_acl = ibm_manager.rias_ops.fetch_ops.get_all_networks_acls(name=acl_name)
        if not configured_acl:
            raise IBMInvalidRequestError("Failed to configure Network ACL with name '{}'".format(acl_name))

        configured_acl = configured_acl[0]
        ibm_network_acl.resource_id = configured_acl.resource_id
        for rule in ibm_network_acl.rules.all():
            for rule_ in configured_acl.rules.all():
                if rule.name == rule_.name:
                    rule.resource_id = rule_.id
                    break

        if not ibm_network_acl.rules.all():
            for rule in configured_acl.rules.all():
                ibm_network_acl.rules.append(rule.make_copy())
        doosradb.session.commit()

        for subnet in subnets_to_configure:
            ibm_manager.rias_ops.attach_acl_to_subnet(subnet)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            cloud.status = INVALID
        if ibm_network_acl:
            ibm_network_acl.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_network_acl.status = CREATED
        for rule in ibm_network_acl.rules.all():
            rule.status = CREATED
        doosradb.session.commit()

    return ibm_network_acl


def configure_network_acl_rule(acl_id, rule_name, data):
    """
    This request creates a new network ACL from a network ACL template. The network ACL template
    object is structured in the same way as a retrieved network ACL, and contains the information
    necessary to create the new network ACL
    :return:
    """
    ibm_network_acl_rule = None
    network_acl = IBMNetworkAcl.query.get(acl_id)
    if not network_acl:
        current_app.logger.debug("IBM Network ACL {} not found".format(acl_id))
        return

    current_app.logger.info("Deploying IBM Network ACL Rule '{name}' on IBM Cloud".format(name=rule_name))
    try:
        ibm_manager = IBMManager(network_acl.ibm_cloud, network_acl.region)
        existing_rule = ibm_manager.rias_ops.fetch_ops.get_all_network_acl_rules(
            network_acl.resource_id, data['action'], data.get('destination'), data['direction'], data.get('source'),
            data['protocol'], data.get('port_max'), data.get('port_min'), data.get('source_port_max'),
            data.get('source_port_min'), data.get('code'), data.get('type'))
        if existing_rule:
            raise IBMInvalidRequestError("IBM Network ACL Rule with params already configured in IBM ACL")

        existing_rule = ibm_manager.rias_ops.fetch_ops.get_all_network_acl_rules(network_acl.resource_id, rule_name)
        if existing_rule:
            raise IBMInvalidRequestError(
                "IBM Network ACL Rule with name '{name}' already exists".format(name=rule_name))

        ibm_network_acl_rule = IBMNetworkAclRule(rule_name, data['action'], data.get('destination'), data['direction'],
                                                 data.get('source'), data['protocol'], data.get('port_max'),
                                                 data.get('port_min'), data.get('source_port_max'),
                                                 data.get('source_port_min'), data.get('code'), data.get('type'))
        network_acl.rules.append(ibm_network_acl_rule)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_network_acl_rule(ibm_network_acl_rule)
        configured_acl_rule = ibm_manager.rias_ops.fetch_ops.get_all_network_acl_rules(network_acl.resource_id,
                                                                                       ibm_network_acl_rule.name)
        if configured_acl_rule:
            configured_acl_rule = configured_acl_rule[0]
            ibm_network_acl_rule.resource_id = configured_acl_rule.resource_id

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            network_acl.ibm_cloud.status = INVALID
        if ibm_network_acl_rule:
            ibm_network_acl_rule.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_network_acl_rule.status = CREATED
        doosradb.session.commit()
    return ibm_network_acl_rule


def delete_network_acl(ibm_network_acl):
    """
    This request deletes a network ACL. This operation cannot be reversed. For this request to succeed,
    the network ACL must not be the default network ACL for any VPCs, and the network ACL must not be
    attached to any subnets.
    :return:
    """
    current_app.logger.info("Deleting Network ACL '{name}' on IBM Cloud '{cloud}'".format(
        name=ibm_network_acl.name, cloud=ibm_network_acl.ibm_cloud.name))
    try:
        ibm_manager = IBMManager(ibm_network_acl.ibm_cloud, ibm_network_acl.region)
        existing_network_acl = ibm_manager.rias_ops.fetch_ops.get_all_networks_acls(ibm_network_acl.name)
        if existing_network_acl:
            existing_network_acl = existing_network_acl[0]
            if existing_network_acl.vpc_id:
                raise IBMInvalidRequestError(
                    "IBM Network ACL '{name}' has VPC network tied".format(name=ibm_network_acl.name))
            if existing_network_acl.subnets.all():
                raise IBMInvalidRequestError(
                    "IBM Network ACL '{name}' has subnets tied".format(name=ibm_network_acl.name))
            ibm_manager.rias_ops.delete_network_acl(existing_network_acl)
        ibm_network_acl.status = DELETED
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_network_acl.ibm_cloud.status = INVALID
        if ibm_network_acl:
            ibm_network_acl.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ibm_network_acl.status = DELETED
        doosradb.session.delete(ibm_network_acl)
        doosradb.session.commit()
        return True


def delete_network_acl_rule(ibm_network_acl_rule):
    """
    This request deletes a network ACL Rule.
    :return:
    """
    current_app.logger.info("Deleting Network ACL Rule '{name}' on IBM Cloud '{cloud}'".format(
        name=ibm_network_acl_rule.name, cloud=ibm_network_acl_rule.ibm_network_acl.ibm_cloud.name))
    try:
        ibm_manager = IBMManager(ibm_network_acl_rule.ibm_network_acl.ibm_cloud,
                                 ibm_network_acl_rule.ibm_network_acl.region)
        existing_network_acl_rule = ibm_manager.rias_ops.fetch_ops.get_all_networks_acls(ibm_network_acl_rule.name)
        if existing_network_acl_rule:
            ibm_manager.rias_ops.delete_network_acl_rule(existing_network_acl_rule[0])
        ibm_network_acl_rule.status = DELETED
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_network_acl_rule.cloud.status = INVALID
        if ibm_network_acl_rule:
            ibm_network_acl_rule.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ibm_network_acl_rule.status = DELETED
        doosradb.session.delete(ibm_network_acl_rule)
        doosradb.session.commit()
        return True
