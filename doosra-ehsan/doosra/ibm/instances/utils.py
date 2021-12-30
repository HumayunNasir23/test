import logging
import random
from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, ERROR_CREATING, ERROR_DELETING, DELETED
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.instances.consts import *
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.models import IBMFloatingIP, IBMInstance, IBMNetworkInterface, IBMSshKey, IBMSubnet, \
    IBMVolume, IBMVolumeAttachment, IBMVpcNetwork, IBMSecurityGroup

LOGGER = logging.getLogger("doosra/ibm/instances/utils.py")


def get_volume_name(volume_name):
    """Return volume name less than 63 string with a unique string at the end"""
    volume_name_ = volume_name if len(volume_name) < 37 else volume_name[20:]
    volume_name_ = "v" + volume_name_ + "-" + str(random.randint(1, 999))
    return volume_name_


def configure_ibm_instance(name, vpc_id, data):
    from doosra.ibm.common.utils import configure_and_save_obj_confs
    """
    This request provisions a new instance from an instance template.  The instance template object is
    structured in the same way as a retrieved instance,  and contains the information necessary to provision
    the new instance. The instance is automatically started.
    :return:
    """
    ibm_instance, objs_to_configure = None, list()
    ibm_vpc_network = IBMVpcNetwork.query.get(vpc_id)
    if not ibm_vpc_network:
        current_app.logger.debug("IBM VPC Network with ID {} not found".format(vpc_id))
        return

    current_app.logger.info("Deploying IBM Instance '{name}' on IBM Cloud".format(name=name))
    try:
        ibm_manager = IBMManager(ibm_vpc_network.ibm_cloud, ibm_vpc_network.region)
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])
        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))
        existing_resource_group = existing_resource_group[0]

        existing_instance = ibm_manager.rias_ops.fetch_ops.get_all_instances(name)
        if existing_instance:
            raise IBMInvalidRequestError("IBM VSI with name '{}' already configured".format(name))

        existing_vpc = ibm_manager.rias_ops.fetch_ops.get_all_vpcs(ibm_vpc_network.name)
        if not existing_vpc:
            raise IBMInvalidRequestError("IBM VPC Network with name '{}' not found".format(ibm_vpc_network.name))

        existing_instance_profile = ibm_manager.rias_ops.fetch_ops.get_all_instance_profiles(data['instance_profile'])
        if not existing_instance_profile:
            raise IBMInvalidRequestError("IBM Instance Profile '{}' not found".format(data['instance_profile']))
        existing_instance_profile = existing_instance_profile[0]

        existing_image = ibm_manager.rias_ops.fetch_ops.get_all_images(data['image'])
        if not existing_image:
            raise IBMInvalidRequestError("IBM Image with name '{}' not found".format(data['image']))
        existing_image = existing_image[0]

        ssh_keys = list()
        if data.get('ssh_keys'):
            for ssh_key in data['ssh_keys']:
                existing_ssh_key = ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys(public_key=ssh_key)
                if existing_ssh_key:
                    ibm_ssh_key = existing_ssh_key[0]
                else:
                    ssh_key_name = ibm_manager.rias_ops.fetch_ops.get_available_ssh_key_name()
                    ibm_ssh_key = IBMSshKey(
                        ssh_key_name, "rsa", ssh_key, ibm_vpc_network.region, cloud_id=ibm_vpc_network.ibm_cloud.id)
                    objs_to_configure.append(ibm_ssh_key)
                ssh_keys.append(ibm_ssh_key)

        volume_attachments = list()
        if data.get('volume_attachments'):
            for volume_attachment in data['volume_attachments']:
                ibm_boot_volume_attachment = IBMVolumeAttachment(
                    volume_attachment['name'], type_="data", is_delete=volume_attachment['auto_delete'])
                volume_profile = ibm_manager.rias_ops.fetch_ops.get_all_volume_profiles(
                    volume_attachment['volume_profile_name'])
                if volume_profile:
                    volume_profile = volume_profile[0]
                ibm_volume = IBMVolume(
                    name=volume_attachment['name'], capacity=volume_attachment['capacity'], zone=data['zone'],
                    encryption="provider_managed", cloud_id=ibm_vpc_network.ibm_cloud.id, region=ibm_vpc_network.region)
                ibm_volume.volume_profile = volume_profile
                ibm_boot_volume_attachment.volume = ibm_volume
                volume_attachments.append(ibm_boot_volume_attachment)

        volume_profile = ibm_manager.rias_ops.fetch_ops.get_all_volume_profiles(name="general-purpose")
        if volume_profile:
            volume_profile = volume_profile[0]
        ibm_volume = IBMVolume(
            name=VOLUME_NAME.format(name), capacity=100, zone=data['zone'], iops=3000, encryption="provider_managed",
            cloud_id=ibm_vpc_network.ibm_cloud.id, region=ibm_vpc_network.region)
        ibm_boot_volume_attachment = IBMVolumeAttachment(
            VOLUME_ATTACHMENT_NAME.format(name), type_="boot", is_delete=True)
        ibm_volume.volume_profile = volume_profile
        ibm_boot_volume_attachment.volume = ibm_volume
        volume_attachments.append(ibm_boot_volume_attachment)

        network_interfaces_to_add = list()
        if data.get('network_interfaces'):
            interface_count = 0
            for interface in data['network_interfaces']:
                ibm_network_interface = IBMNetworkInterface(
                    NETWORK_INTERFACE_NAME.format(name, interface_count), is_primary=interface['is_primary'])
                interface_count = interface_count + 1
                subnet = doosradb.session.query(IBMSubnet).filter_by(id=interface['subnet_id']).first()
                existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(
                    name=subnet.name, zone=subnet.zone, vpc=subnet.ibm_vpc_network.name)
                if not existing_subnet:
                    raise IBMInvalidRequestError("IBM Subnet with name '{}' not found".format(subnet.name))
                security_groups = list(
                    map(lambda security_group_: doosradb.session.query(IBMSecurityGroup).filter_by(
                        id=security_group_).first().make_copy(), interface['security_groups']))

                for security_group in security_groups:
                    existing_security_group = ibm_manager.rias_ops.fetch_ops.get_all_security_groups(
                        security_group.name, ibm_vpc_network.name)

                    if not existing_security_group:
                        raise IBMInvalidRequestError(
                            "IBM Security Group with name '{}' not found".format(security_group.name))

                ibm_network_interface.ibm_subnet = subnet.make_copy()
                ibm_network_interface.security_groups.extend(security_groups)
                if interface.get('reserve_floating_ip'):
                    floating_ip_name = ibm_manager.rias_ops.fetch_ops.get_available_floating_ip_name()
                    ibm_floating_ip = IBMFloatingIP(
                        name=floating_ip_name, zone=data["zone"], cloud_id=ibm_vpc_network.ibm_cloud.id,
                        region=ibm_vpc_network.region)
                    ibm_network_interface.floating_ip = ibm_floating_ip
                network_interfaces_to_add.append(ibm_network_interface)

        ibm_instance = IBMInstance(
            name=name, zone=data['zone'], user_data=data.get('user_data'), cloud_id=ibm_vpc_network.ibm_cloud.id,
            region=ibm_vpc_network.region
        )
        ibm_instance.ibm_image = existing_image
        ibm_instance.ibm_resource_group = existing_resource_group
        ibm_instance.ibm_instance_profile = existing_instance_profile
        ibm_instance.network_interfaces = network_interfaces_to_add
        ibm_instance.volume_attachments = volume_attachments
        ibm_instance.ssh_keys = ssh_keys
        ibm_instance = ibm_instance.make_copy().add_update_db(ibm_vpc_network)
        objs_to_configure.append(ibm_instance)
        for ibm_network_interface in ibm_instance.network_interfaces.all():
            if ibm_network_interface.floating_ip:
                objs_to_configure.append(ibm_network_interface.floating_ip)

        for obj in objs_to_configure:
            configure_and_save_obj_confs(ibm_manager, obj, ibm_vpc_network)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_vpc_network.ibm_cloud.status = INVALID
        for obj in objs_to_configure:
            if not obj.status == CREATED:
                obj.status = ERROR_CREATING
        if ibm_instance:
            ibm_instance.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_instance.status = CREATED
        doosradb.session.commit()

    return ibm_instance


def delete_ibm_instance(instance):
    """
    This request deletes an instance. This operation cannot be reversed. Any floating IPs associated
    with the instance's network interfaces are implicitly disassociated.
    :param instance:
    :return:
    """
    objs_to_delete, objs_to_update = list(), list()
    current_app.logger.info("Deleting IBM VSI '{name}' on IBM Cloud".format(name=instance.name))
    try:
        ibm_manager = IBMManager(instance.ibm_cloud, instance.ibm_vpc_network.region)
        existing_instance = ibm_manager.rias_ops.fetch_ops.get_all_instances(name=instance.name)
        if existing_instance:
            objs_to_delete.append(existing_instance[0])
            for interface in existing_instance[0].network_interfaces.all():
                if interface.floating_ip:
                    objs_to_delete.append(interface.floating_ip)
                    objs_to_update.append(interface)

        for obj in objs_to_update:
            if obj.__class__.__name__ == IBMNetworkInterface.__name__:
                ibm_manager.rias_ops.detach_floating_ip_for_interface(obj)

        for obj in objs_to_delete:
            if isinstance(obj, IBMInstance):
                ibm_manager.rias_ops.stop_instance(obj)
            ibm_manager.rias_ops.push_obj_confs(obj, delete=True)
            obj.status = DELETED
            doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            instance.cloud.status = INVALID
        for obj in objs_to_delete:
            if not obj.status == DELETED:
                obj.status = ERROR_DELETING
        instance.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        for interface in instance.network_interfaces.all():
            if interface.floating_ip:
                doosradb.session.delete(interface.floating_ip)
                doosradb.session.commit()

            if interface.security_groups:
                interface.security_groups = list()

        for attachment in instance.volume_attachments.all():
            if attachment.volume:
                doosradb.session.delete(attachment.volume)
                doosradb.session.commit()

            doosradb.session.delete(attachment)
            doosradb.session.commit()

        instance.status = DELETED
        doosradb.session.delete(instance)
        doosradb.session.commit()
        return True
