from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, DELETED, ERROR_CREATING, ERROR_DELETING
from doosra.gcp.clouds.consts import INVALID
from doosra.gcp.managers.exceptions import CloudAuthError, CloudExecuteError, CloudInvalidRequestError
from doosra.gcp.managers.gcp_manager import GCPManager
from doosra.models.gcp_models import GcpDisk, GcpInstance, GcpTag, InstanceDisk, GcpNetworkInterface, \
    GcpVpcNetwork


def deploy_instance(cloud_project, zone, name, machine_type, interfaces, disks, network_tags, description=None):
    """
    Create Instance on Google cloud platform
    :return:
    """
    gcp_instance = None
    current_app.logger.info("Deploying Instance '{name}' on GCP cloud project '{project}'".format(
        name=name, project=cloud_project.name))
    try:
        gcp_manager = GCPManager(cloud_project.gcp_cloud)
        instances = gcp_manager.compute_engine_operations.fetch_ops.get_all_instances(
            name=name, project_id=cloud_project.project_id)
        if instances:
            raise CloudInvalidRequestError("Instance with name '{}' already created".format(name))

        gcp_instance = GcpInstance(name=name, description=description, zone=zone, machine_type=machine_type,
                                   cloud_project_id=cloud_project.id)
        for interface in interfaces:
            gcp_vpc_network = doosradb.session.query(GcpVpcNetwork).filter_by(id=interface.get('vpc_id')).first()
            vpc_network = gcp_manager.compute_engine_operations.fetch_ops.get_vpc_networks(cloud_project.project_id,
                                                                                           gcp_vpc_network.name)
            if not vpc_network:
                raise CloudInvalidRequestError("VPC network with name '{}' not found".format(gcp_vpc_network.name))

            gcp_subnet = None
            for subnet in gcp_vpc_network.subnets.all():
                if interface.get('subnetwork_id') == subnet.id:
                    gcp_subnet = subnet
                    break

            if not gcp_subnet:
                raise CloudInvalidRequestError("GCP Subnet '{}' not found".format(interface.get('subnetwork_id')))

            for tag in network_tags:
                gcp_tag = gcp_vpc_network.tags.filter_by(tag=tag).first()
                if not gcp_tag:
                    gcp_tag = GcpTag(tag)
                    gcp_tag.gcp_vpc_network = gcp_vpc_network

                gcp_instance.tags.append(gcp_tag)

            gcp_network_interface = GcpNetworkInterface(
                name=interface.get("name"), primary_internal_ip=interface.get("primary_internal_ip"),
                external_ip=interface.get("external_ip"))
            gcp_network_interface.gcp_vpc_network = gcp_vpc_network
            gcp_network_interface.gcp_subnet = gcp_subnet
            gcp_instance.interfaces.append(gcp_network_interface)

        for disk in disks:
            gcp_disk = GcpDisk(name=disk.get("name"), zone=zone, disk_type=disk.get("type"),
                               disk_size=disk.get("size"), source_image=disk.get("source_image"))
            gcp_instance_disk = InstanceDisk()
            gcp_instance_disk.boot = disk.get("boot")
            gcp_instance_disk.auto_delete = disk.get("auto_delete")
            gcp_instance_disk.mode = disk.get("mode")
            gcp_instance_disk.disk = gcp_disk
            gcp_instance_disk.instance = gcp_instance

        doosradb.session.add(gcp_instance)
        doosradb.session.commit()
        gcp_manager.compute_engine_operations.push_obj_confs(gcp_instance, cloud_project.project_id)

        existing_instance = gcp_manager.compute_engine_operations.fetch_ops.get_instances(
            cloud_project.project_id, gcp_instance.zone, gcp_instance.name)
        if not existing_instance:
            raise CloudInvalidRequestError("Error configuring GCP instance '{}'".format(gcp_instance.name))

        existing_instance = existing_instance[0]
        for interface in gcp_instance.interfaces.all():
            for interface_ in existing_instance.interfaces.all():
                if interface.gcp_vpc_network.name == interface_.gcp_vpc_network.name and \
                        interface.gcp_subnet.name == interface_.gcp_subnet.name:
                    interface.primary_internal_ip = interface_.primary_internal_ip
                    doosradb.session.commit()
                    break

    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            cloud_project.gcp_cloud.status = INVALID
        if gcp_instance:
            gcp_instance.status = ERROR_CREATING
        doosradb.session.commit()
        return None, ex.msg
    else:
        gcp_instance.status = CREATED
        doosradb.session.commit()
        return gcp_instance, None


def delete_instance(instance):
    """
    Delete Instance from Google cloud platform
    :return:
    """
    current_app.logger.info("Deleting GCP Instance '{name}' and cloud project '{project}'".format(
        name=instance.name, project=instance.gcp_cloud_project.name))
    try:
        gcp_manager = GCPManager(instance.gcp_cloud_project.gcp_cloud)
        current_app.logger.debug("Deleting Instance with name '{}'".format(instance.name))
        existing_instance = gcp_manager.compute_engine_operations.fetch_ops.get_all_instances(
            instance.gcp_cloud_project.project_id,
            name=instance.name)
        if existing_instance:
            gcp_manager.compute_engine_operations.push_obj_confs(
                instance, instance.gcp_cloud_project.project_id, delete=True)

        for interface in instance.interfaces:
            if interface.gcp_address:
                existing_address = gcp_manager.compute_engine_operations.fetch_ops.get_addresses(
                    instance.gcp_cloud_project.project_id, name=interface.gcp_address.name,
                    region=interface.gcp_address.region)
                if existing_address:
                    gcp_manager.compute_engine_operations.push_obj_confs(
                        interface.gcp_address, instance.gcp_cloud_project.project_id, delete=True)
                interface.gcp_address.status = DELETED
                doosradb.session.commit()

    except (CloudAuthError, CloudExecuteError, CloudInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, CloudAuthError):
            instance.gcp_cloud_project.gcp_cloud.status = INVALID
        instance.status = ERROR_DELETING
        doosradb.session.commit()
        return False, ex.msg
    else:
        for interface in instance.interfaces:
            if interface.gcp_address:
                doosradb.session.delete(interface.gcp_address)

        for disk in instance.disks:
            doosradb.session.delete(disk)

        tags = instance.tags.all()
        doosradb.session.delete(instance)

        for tag in tags:
            if not tag.gcp_instances:
                doosradb.session.delete(tag)

        doosradb.session.delete(instance)
        doosradb.session.commit()
        return True, None
