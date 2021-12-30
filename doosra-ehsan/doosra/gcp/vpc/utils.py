from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, CREATING, DELETING, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.gcp.clouds.consts import INVALID
from doosra.gcp.managers.exceptions import CloudAuthError, CloudExecuteError, CloudInvalidRequestError
from doosra.gcp.managers.gcp_manager import GCPManager
from doosra.models.gcp_models import GcpCloudProject, GcpSecondaryIpRange, GcpSubnet, GcpVpcNetwork


def get_latest_vpc_networks(project_id):
    """
    Get latest VPC networks from cloud account
    :param project_id:
    :return:
    """
    cloud_project = doosradb.session.query(GcpCloudProject).filter_by(id=project_id).first()
    if not cloud_project:
        return
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        vpc_networks = gcp_manager.compute_engine_operations.fetch_ops.get_vpc_networks(cloud_project.project_id)
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()
    else:
        return vpc_networks


def deploy_vpc_network(cloud_project, vpc, description, subnets=None):
    """
    Create and deploy VPC network on Google cloud platform
    :return:
    """
    objs_to_configure, vpc_network = list(), None
    current_app.logger.info("Deploying VPC '{name}' on GCP cloud project '{project}'".format(
        name=vpc, project=cloud_project.name))
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        vpc_networks = gcp_manager.compute_engine_operations.fetch_ops.get_vpc_networks(
            project_id=cloud_project.project_id)
        if len(vpc_networks) >= 5:
            raise CloudInvalidRequestError("Maximum limit of '5' reached for VPC networks")

        vpc_network_names = [vpc.name for vpc in vpc_networks]
        if vpc in vpc_network_names:
            raise CloudInvalidRequestError("VPC network with name '{}' already configured".format(vpc))

        vpc_network = GcpVpcNetwork(name=vpc, description=description, auto_create_subnetworks=False,
                                    routing_mode="REGIONAL")
        vpc_network.gcp_cloud_project = cloud_project
        objs_to_configure.append(vpc_network)

        if subnets:
            existing_subnets = gcp_manager.compute_engine_operations.fetch_ops.get_all_vpc_subnets(
                cloud_project.project_id)
            for subnet in subnets:
                if subnet['name'] in [s_.name for s_ in existing_subnets]:
                    raise CloudInvalidRequestError(
                        "Subnet with name {subnet} already exists in Cloud Project '{project}'".format(
                            subnet=subnet['name'], project=cloud_project.project_id))

                if subnet['ip_range'] in [s_.name for s_ in existing_subnets]:
                    raise CloudInvalidRequestError(
                        "Subnet with IP range {ip_range} already exists in Cloud Project '{project}'".format(
                            ip_range=subnet['ip_range'], project=cloud_project.project_id))

                gcp_region = gcp_manager.compute_engine_operations.fetch_ops.get_regions(
                    name=subnet['region'], project_id=cloud_project.project_id)
                if not gcp_region:
                    raise CloudInvalidRequestError("Region '{}' doesn't exist for GCP".format(subnet['name']))

                gcp_region = gcp_region[0]
                gcp_subnet = GcpSubnet(name=subnet['name'], ip_cidr_range=subnet['ip_range'],
                                       description=subnet.get("description"), region=gcp_region)
                if subnet.get('secondary_ip_ranges'):
                    for ip_range in subnet.get('secondary_ip_ranges'):
                        secondary_ip_range = GcpSecondaryIpRange(name=ip_range['name'],
                                                                 ip_cidr_range=ip_range['ip_range'])
                        gcp_subnet.secondary_ip_ranges.append(secondary_ip_range)

                vpc_network.subnets.append(gcp_subnet)
                objs_to_configure.append(gcp_subnet)

        doosradb.session.add(vpc_network)
        doosradb.session.commit()
        for obj in objs_to_configure:
            gcp_manager.compute_engine_operations.push_obj_confs(obj, cloud_project.project_id)
            if obj.__class__.__name__ == GcpVpcNetwork.__name__:
                continue
            obj.status = CREATED
            doosradb.session.commit()
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()
        if vpc_network:
            for subnet in vpc_network.subnets.all():
                if subnet.status == CREATING:
                    subnet.status = ERROR_CREATING
            vpc_network.status = ERROR_CREATING
            doosradb.session.commit()
        return None, ex.msg
    else:
        vpc_network.status = CREATED
        doosradb.session.commit()
        return vpc_network, None


def delete_vpc_network(vpc):
    """
    Delete VPC network from Google cloud platform
    :return:
    """
    objs_to_delete = list()
    current_app.logger.info("Deleting GCP VPC '{name}' and cloud project '{project}'".format(
        name=vpc.name, project=vpc.gcp_cloud_project.name))
    try:
        gcp_manager = GCPManager(vpc.gcp_cloud_project.gcp_cloud)
        current_app.logger.debug("Deleting VPC network with name '{}'".format(vpc.name))
        existing_firewall_rules = gcp_manager.compute_engine_operations.fetch_ops.get_firewall_rules(
            project_id=vpc.gcp_cloud_project.project_id, vpc_network=vpc.name)
        for firewall in vpc.firewall_rules.all():
            found = False
            for firewall_ in existing_firewall_rules:
                if firewall.name == firewall_.name:
                    found = True
                    break
            if found:
                firewall.status = DELETING
                objs_to_delete.append(firewall)
            else:
                firewall.status = DELETED
            doosradb.session.commit()

        existing_instances = gcp_manager.compute_engine_operations.fetch_ops.get_all_instances(
            vpc.gcp_cloud_project.project_id, vpc_network=vpc.name)
        for network_interface in vpc.network_interfaces.all():
            found = False
            for instance in existing_instances:
                if instance.name == network_interface.gcp_instance.name:
                    found = True
                    break

            if found:
                objs_to_delete.append(network_interface.gcp_instance)
            else:
                network_interface.gcp_instance.status = DELETED
            doosradb.session.commit()

        existing_vpc = gcp_manager.compute_engine_operations.fetch_ops.get_vpc_networks(
            vpc.gcp_cloud_project.project_id, name=vpc.name)
        if existing_vpc:
            existing_vpc = existing_vpc[0]
            for subnet in vpc.subnets.all():
                found = False
                for subnet_ in existing_vpc.subnets.all():
                    if subnet.name == subnet_.name:
                        found = True
                        break
                if found:
                    objs_to_delete.append(subnet)
                else:
                    subnet.status = DELETED
            doosradb.session.commit()
            objs_to_delete.append(vpc)

        for obj in objs_to_delete:
            obj.status = DELETING
            doosradb.session.commit()
            gcp_manager.compute_engine_operations.push_obj_confs(obj, vpc.gcp_cloud_project.project_id, delete=True)
            if obj.__class__.__name__ == GcpVpcNetwork.__name__:
                continue
            obj.status = DELETED
            doosradb.session.commit()
    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            vpc.gcp_cloud_project.gcp_cloud.status = INVALID
            doosradb.session.commit()

        vpc.status = ERROR_DELETING
        for subnet in vpc.subnets.all():
            if subnet.status == DELETING:
                subnet.status = ERROR_DELETING

        for firewall in vpc.firewall_rules.all():
            if firewall.status == DELETING:
                firewall.status = ERROR_DELETING

        for network_interface in vpc.network_interfaces.all():
            if network_interface.gcp_instance.status == DELETING:
                network_interface.gcp_instance.status = ERROR_DELETING

        doosradb.session.commit()
        return None, ex.msg
    else:
        vpc.status = DELETED
        doosradb.session.delete(vpc)
        doosradb.session.commit()
        return True, None


def update_vpc_network(vpc, subnets=None):
    """
    Update VPC network on Google cloud platform
    """
    current_app.logger.info("Updating GCP VPC '{name}' on cloud project '{project}'".format(
        name=vpc.name, project=vpc.gcp_cloud_project.name))
    objs_to_add, objs_to_update, objs_to_delete = list(), list(), list()
    try:
        gcp_manager = GCPManager(vpc.gcp_cloud_project.gcp_cloud)
        existing_vpc = gcp_manager.compute_engine_operations.fetch_ops.get_vpc_networks(
            vpc.gcp_cloud_project.project_id, name=vpc.name)
        if not existing_vpc:
            raise CloudInvalidRequestError("VPC network with name '{}' not found".format(vpc.name))

        existing_vpc = existing_vpc[0]
        gcp_subnets, to_ignore, to_remove = list(), list(), list()
        for existing_subnet in existing_vpc.subnets.all():
            found = False
            for subnet in subnets:
                if existing_subnet.name == subnet['name']:
                    found = True
                    break

            if found:
                to_ignore.append(existing_subnet)
            else:
                to_remove.append(existing_subnet)

        for subnet in to_remove:
            objs_to_delete.append(subnet)

        for subnet in subnets:
            gcp_region = gcp_manager.compute_engine_operations.fetch_ops.get_regions(vpc.gcp_cloud_project.project_id,
                                                                                     name=subnet['region'])
            if not gcp_region:
                raise CloudInvalidRequestError("Region '{}' not found for GCP".format(subnet['region']))
            gcp_subnet = GcpSubnet(name=subnet['name'], ip_cidr_range=subnet['ip_range'],
                                   description=subnet.get("description"), region=gcp_region[0])
            if subnet.get('secondary_ip_ranges'):
                for ip_range in subnet['secondary_ip_ranges']:
                    ip_range = GcpSecondaryIpRange(name=ip_range['name'], ip_cidr_range=ip_range['ip_range'])
                    gcp_subnet.secondary_ip_ranges.append(ip_range)

            gcp_subnets.append(gcp_subnet)
            if gcp_subnet.name not in [subnet_.name for subnet_ in to_ignore]:
                objs_to_add.append(gcp_subnet)

            for subnet_ in to_ignore:
                if subnet_.name == gcp_subnet.name and not subnet_.params_eq(gcp_subnet):
                    objs_to_update.append(gcp_subnet)
                    break

        vpc.subnets = gcp_subnets
        vpc_to_add = vpc.make_copy()
        gcp_subnets_to_add = list()
        for subnet in gcp_subnets:
            gcp_subnets_to_add.append(subnet.make_copy())
        vpc_to_add.subnets = gcp_subnets_to_add
        existing_vpc = doosradb.session.query(GcpVpcNetwork).filter_by(
            name=vpc.name, cloud_project_id=vpc.gcp_cloud_project.id).first()
        vpc_to_add.add_update_db(existing_vpc)

        for obj in objs_to_add:
            gcp_manager.compute_engine_operations.push_obj_confs(obj, vpc.gcp_cloud_project.project_id)

        for obj in objs_to_update:
            gcp_manager.compute_engine_operations.push_obj_confs(obj, vpc.gcp_cloud_project.project_id, update=True)

        for obj in objs_to_delete:
            gcp_manager.compute_engine_operations.push_obj_confs(obj, vpc.gcp_cloud_project.project_id, delete=True)

    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            vpc.gcp_cloud_project.gcp_cloud.status = INVALID
        elif isinstance(ex, (CloudExecuteError, CloudInvalidRequestError)):
            doosradb.session.commit()
        return

    return True
