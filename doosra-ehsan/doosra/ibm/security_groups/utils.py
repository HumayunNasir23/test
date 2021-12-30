from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMResourceGroup, IBMSecurityGroupRule, IBMSecurityGroup, IBMVpcNetwork


def configure_ibm_security_group(security_group_name, vpc_id, data):
    """
    This request creates a new security group from a security group template. Each security group is
    scoped to one VPC. Only network interfaces on instances in that VPC can be added to the security group.
    :return:
    """
    ibm_security_group = None
    ibm_vpc = IBMVpcNetwork.query.get(vpc_id)
    if not ibm_vpc:
        current_app.logger.debug("IBM VPC Network {} not found".format(vpc_id))
        return

    current_app.logger.info("Deploying Security Group '{name}' on IBM Cloud".format(name=security_group_name))
    try:
        ibm_manager = IBMManager(ibm_vpc.ibm_cloud, ibm_vpc.region)
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])
        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))

        existing_security_group = ibm_manager.rias_ops.fetch_ops.get_all_security_groups(security_group_name)
        if existing_security_group:
            raise IBMInvalidRequestError(
                "Security Group with name '{}' already configured in region '{}'".format(
                    security_group_name, ibm_vpc.region))
        resource_group = doosradb.session.query(IBMResourceGroup).filter_by(
            name=data['resource_group'], cloud_id=ibm_vpc.ibm_cloud.id).first()
        if not resource_group:
            resource_group = existing_resource_group[0]
            resource_group.ibm_cloud = ibm_vpc.ibm_cloud
            doosradb.session.add(resource_group)
        ibm_security_group = IBMSecurityGroup(security_group_name, region=ibm_vpc.region)
        ibm_security_group.ibm_vpc_network = ibm_vpc
        ibm_security_group.resource_group_id = resource_group.id
        ibm_security_group.ibm_cloud = ibm_vpc.ibm_cloud
        if data.get('rules'):
            for rule in data['rules']:
                ibm_security_group_rule = IBMSecurityGroupRule(
                    rule['direction'], rule['protocol'], rule.get('code'), rule.get('type'), rule.get('port_min'),
                    rule.get('port_max'), rule.get('address'), rule.get('cidr_block'))

                if rule.get('security_group'):
                    ibm_security_group_rule.rule_type = "security-group"

                ibm_security_group.rules.append(ibm_security_group_rule)

        doosradb.session.add(ibm_security_group)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_security_group(ibm_security_group)
        existing_obj = ibm_manager.rias_ops.fetch_ops.list_obj_method_mapper(ibm_security_group)
        if not existing_obj:
            raise IBMInvalidRequestError(
                "Failed to configure IBM Security Group with name '{name}'".format(name=ibm_security_group.name))

        ibm_security_group = existing_obj[0].add_update_db(ibm_vpc)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_vpc.ibm_cloud.status = INVALID

        if ibm_security_group:
            ibm_security_group.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_security_group.status = CREATED
        for rule in ibm_security_group.rules.all():
            rule.status = CREATED
        doosradb.session.commit()

    return ibm_security_group


def configure_ibm_security_group_rule(security_group_id, data):
    """
    This request creates a new security group rule from a security group rule template
    :return:
    """
    ibm_security_group_rule = None
    ibm_security_group = IBMSecurityGroup.query.get(security_group_id)
    if not ibm_security_group:
        current_app.logger.debug("IBM Security Group {} not found".format(security_group_id))
        return
    try:
        ibm_manager = IBMManager(ibm_security_group.ibm_cloud, ibm_security_group.ibm_vpc_network.region)
        existing_rule = ibm_manager.rias_ops.fetch_ops.get_all_security_group_rules(
            ibm_security_group.resource_id, data['direction'], data.get('protocol'), data.get('code'),
            data.get('type'), data.get('port_min'), data.get('port_max'), data.get('address'), data.get('cidr_block'))
        if existing_rule:
            raise IBMInvalidRequestError("IBM Security Group Rule with params already configured in IBM Security Group")

        ibm_security_group_rule = IBMSecurityGroupRule(
            data['direction'], data['protocol'], data.get('code'), data.get('type'), data.get('port_min'),
            data.get('port_max'), data.get('address'), data.get('cidr_block'))
        if data.get('security_group'):
            ibm_security_group_rule.rule_type = "security_group"
        ibm_security_group.rules.append(ibm_security_group_rule)
        doosradb.session.commit()

        response = ibm_manager.rias_ops.create_security_group_rule(ibm_security_group_rule)
        if response:
            ibm_security_group_rule.resource_id = response["id"]
            doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_security_group.ibm_cloud.status = INVALID
        if ibm_security_group_rule:
            ibm_security_group_rule.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_security_group_rule.status = CREATED
        doosradb.session.commit()
    return ibm_security_group_rule


def delete_ibm_security_group(ibm_security_group):
    """
    This request deletes a security group. A security group cannot be deleted if it is referenced by any
    network interfaces or other security group rules. Additionally, a VPC's default security group cannot be
    deleted. This operation cannot be reversed.
    :param ibm_security_group:
    :return:
    """
    current_app.logger.info("Deleting Security Group '{name}' on IBM Cloud '{cloud}'".format(
        name=ibm_security_group.name, cloud=ibm_security_group.ibm_cloud.name))
    try:
        ibm_manager = IBMManager(ibm_security_group.ibm_cloud, ibm_security_group.ibm_vpc_network.region)
        existing_security_group = ibm_manager.rias_ops.fetch_ops.get_all_security_groups(ibm_security_group.name)
        if existing_security_group:
            default_security_group = ibm_manager.rias_ops.fetch_ops.get_vpc_default_security_group(
                ibm_security_group.ibm_vpc_network.resource_id)
            if default_security_group and default_security_group.name == ibm_security_group.name:
                raise IBMInvalidRequestError(
                    "IBM Security Group '{name}' is default for VPC network '{vpc}'".format(
                        name=ibm_security_group.name, vpc=ibm_security_group.ibm_vpc_network.name))
            ibm_manager.rias_ops.delete_security_group(existing_security_group[0])
        ibm_security_group.status = DELETED
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_security_group.ibm_cloud.cloud.status = INVALID
        if ibm_security_group:
            ibm_security_group.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ibm_security_group.status = DELETED
        doosradb.session.delete(ibm_security_group)
        doosradb.session.commit()
        return True


def delete_ibm_security_group_rule(ibm_security_group_rule):
    """
    This request deletes a security group rule. This operation cannot be reversed.
    Removing a security group rule will not end existing connections allowed by that rule.
    :return:
    """
    current_app.logger.info("Deleting Security Group Rule '{id}' on IBM Cloud '{cloud}'".format(
        id=ibm_security_group_rule.id, cloud=ibm_security_group_rule.security_group.ibm_cloud.name))
    try:
        ibm_manager = IBMManager(ibm_security_group_rule.security_group.ibm_cloud,
                                 ibm_security_group_rule.security_group.ibm_vpc_network.region)
        existing_security_group_rule = ibm_manager.rias_ops.fetch_ops.get_all_security_group_rules(
            ibm_security_group_rule.security_group.resource_id,
            security_group_rule_id=ibm_security_group_rule.resource_id)
        if existing_security_group_rule:
            ibm_manager.rias_ops.delete_security_group_rule(ibm_security_group_rule)
        ibm_security_group_rule.status = DELETED
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_security_group_rule.security_group.ibm_cloud.status = INVALID
        if ibm_security_group_rule:
            ibm_security_group_rule.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ibm_security_group_rule.status = DELETED
        doosradb.session.delete(ibm_security_group_rule)
        doosradb.session.commit()
        return True
