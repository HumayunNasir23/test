from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.gcp.clouds.consts import INVALID
from doosra.gcp.managers.exceptions import *
from doosra.gcp.managers.gcp_manager import GCPManager
from doosra.models import GcpFirewallRule, GcpIpProtocol, GcpTag


def create_firewall_rule(vpc, firewall_rule_name, direction, action, tags=None, ip_ranges=None, priority=None,
                         description=None, target_tags=None, ip_protocols=None):
    """
    Deploy a firewall rule on Google Cloud. Returns True if deployed successfully.
    :return:
    """
    cloud_project = vpc.gcp_cloud_project
    project_id = cloud_project.project_id
    current_app.logger.info("Deploying Firewall Rule '{name}' on GCP cloud project '{project}'".format(
        name=firewall_rule_name, project=cloud_project.name))
    gcp_firewall_rule = None
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        firewall_rules = gcp_manager.compute_engine_operations.fetch_ops.get_firewall_rules(
            project_id=project_id, name=firewall_rule_name)
        if firewall_rules:
            raise CloudInvalidRequestError(
                "Firewall Rule with name {name} already configured".format(name=firewall_rule_name))

        existing_vpc_network = gcp_manager.compute_engine_operations.fetch_ops.get_vpc_networks(project_id, vpc.name)
        if not existing_vpc_network:
            raise CloudInvalidRequestError("VPC Network with name {name} not found".format(name=vpc.name))

        gcp_firewall_rule = GcpFirewallRule(
            name=firewall_rule_name, description=description, direction=direction, action=action, priority=priority,
            ip_ranges=ip_ranges)

        if tags:
            for tag_id in tags:
                gcp_tag = doosradb.session.query(GcpTag).filter_by(id=tag_id).first()
                if gcp_tag:
                    gcp_firewall_rule.tags.append(gcp_tag)

        if target_tags:
            for tag_id in target_tags:
                gcp_tag = doosradb.session.query(GcpTag).filter_by(id=tag_id).first()
                if gcp_tag:
                    gcp_firewall_rule.target_tags.append(gcp_tag)

        if ip_protocols:
            for ip_protocol in ip_protocols:
                gcp_ip_protocol = GcpIpProtocol(ip_protocol.get('protocol'), ip_protocol.get('ports'))
                gcp_firewall_rule.ip_protocols.append(gcp_ip_protocol)
        else:
            ip_protocol = GcpIpProtocol(protocol="all")
            gcp_firewall_rule.ip_protocols.append(ip_protocol)

        gcp_firewall_rule.gcp_vpc_network = vpc
        doosradb.session.add(gcp_firewall_rule)
        doosradb.session.commit()
        gcp_manager.compute_engine_operations.push_obj_confs(gcp_firewall_rule, project_id)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
        if gcp_firewall_rule:
            gcp_firewall_rule.status = ERROR_CREATING
        doosradb.session.commit()
        return None, ex.msg
    else:
        gcp_firewall_rule.status = CREATED
        doosradb.session.commit()
        return gcp_firewall_rule, None


def delete_firewall_rule(firewall_rule):
    """
    Delete Firewall rule from Google Cloud.
    :return:
    """
    cloud_project = firewall_rule.gcp_vpc_network.gcp_cloud_project
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        existing_firewall = gcp_manager.compute_engine_operations.fetch_ops.get_firewall_rules(
            cloud_project.project_id, name=firewall_rule.name)
        if existing_firewall:
            existing_firewall = existing_firewall[0]
            current_app.logger.debug("Deleting GCP Firewall with with name '{}'".format(firewall_rule.name))
            gcp_manager.compute_engine_operations.push_obj_confs(
                existing_firewall, cloud_project.project_id, delete=True)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
        firewall_rule.status = ERROR_DELETING
        doosradb.session.commit()
        return None, ex.msg
    else:
        firewall_rule.status = DELETED
        doosradb.session.delete(firewall_rule)
        doosradb.session.commit()
        return True, None
