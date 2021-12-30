from flask import current_app

from doosra import db as doosradb
from doosra.common.consts import CREATED, CREATING, DELETED, DELETING, ERROR_CREATING, ERROR_DELETING
from doosra.common.utils import get_obj_type, validate_ip_in_range
from doosra.ibm.clouds.consts import INVALID
from doosra.ibm.common.utils import configure_and_save_obj_confs
from doosra.ibm.instances.consts import NETWORK_INTERFACE_NAME, VOLUME_NAME, VOLUME_ATTACHMENT_NAME
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.ibm_manager import IBMManager
from doosra.ibm.managers.operations.rias.consts import GENERATION
from doosra.ibm.public_gateways.consts import PUBLIC_GATEWAY_NAME
from doosra.models import IBMCloud, IBMFloatingIP, IBMHealthCheck, IBMIKEPolicy, IBMIPSecPolicy, IBMInstance, \
    IBMListener, IBMLoadBalancer, IBMVpcRoute, IBMNetworkAcl, IBMNetworkInterface, IBMPool, IBMPoolMember, \
    IBMPublicGateway, IBMSshKey, IBMSubnet, IBMVolume, IBMVolumeAttachment, IBMVpcNetwork, IBMAddressPrefix, \
    IBMNetworkAclRule, IBMSecurityGroup, IBMSecurityGroupRule, IBMVpnGateway, IBMVpnConnection, IBMResourceGroup


def configure_ibm_vpc(cloud_id, name, region, data):
    """
    Configure VPC on IBM cloud. A VPC is a virtual network that belongs to an account and
    provides logical isolation from other networks. A VPC is made up of resources in one
    or more zones. VPCs are global, and each can contain resources in zones from any region.
    :return:
    """
    ibm_vpc_network, objs_to_configure = None, list()
    cloud = IBMCloud.query.get(cloud_id)
    if not cloud:
        current_app.logger.debug("IBM Cloud with ID '{}' not found".format(cloud_id))
        return

    current_app.logger.info(
        "Deploying VPC '{name}' in region '{region} 'on IBM Cloud".format(name=name, region=region))
    try:
        ibm_manager = IBMManager(cloud, region)
        existing_resource_group = ibm_manager.resource_ops.fetch_ops.get_resource_groups(data['resource_group'])
        if not existing_resource_group:
            raise IBMInvalidRequestError("Resource Group with name '{}' not configured".format(data['resource_group']))

        existing_vpc = ibm_manager.rias_ops.fetch_ops.get_all_vpcs(name=name)
        if existing_vpc:
            raise IBMInvalidRequestError(
                "VPC with name '{}' already configured in region '{}'".format(name, region))

        ibm_vpc_network = IBMVpcNetwork(
            name=name, region=region, classic_access=data.get('classic_access'), cloud_id=cloud_id,
            address_prefix_management=data.get('address_prefix_management'))
        ibm_vpc_network.ibm_resource_group = existing_resource_group[0]
        objs_to_configure.append(ibm_vpc_network)

        if data.get('address_prefixes'):
            for addr_prefix in data['address_prefixes']:
                ibm_address_prefix = IBMAddressPrefix(
                    addr_prefix.get('name'), addr_prefix['zone'], addr_prefix['address'],
                    is_default=addr_prefix.get('is_default'))

                if not ibm_address_prefix.is_default:
                    objs_to_configure.append(ibm_address_prefix)

                ibm_vpc_network.address_prefixes.append(ibm_address_prefix)

        if data.get('public_gateways'):
            for public_gateway in data['public_gateways']:
                ibm_public_gateway = IBMPublicGateway(
                    name=public_gateway['name'], zone=public_gateway['zone'], region=ibm_vpc_network.region)
                ibm_vpc_network.public_gateways.append(ibm_public_gateway)
                objs_to_configure.append(ibm_public_gateway)

        if data.get('network_acls'):
            for acl in data['network_acls']:
                ibm_acl = IBMNetworkAcl(acl['name'], region)
                for rule in acl['rules']:
                    ibm_rule = IBMNetworkAclRule(
                        rule['name'], rule['action'], rule.get('destination'), rule['direction'], rule.get('source'),
                        rule['protocol'], rule.get('port_max'), rule.get('port_min'), rule.get('source_port_max'),
                        rule.get('source_port_min'), rule.get('code'), rule.get('type'))
                    ibm_acl.rules.append(ibm_rule)
                objs_to_configure.append(ibm_acl)

        if data.get('ssh_keys'):
            for ssh_key in data['ssh_keys']:
                ibm_ssh_key = IBMSshKey(
                    ssh_key['name'], "rsa", ssh_key['public_key'], ibm_vpc_network.region, cloud_id=cloud_id)
                objs_to_configure.append(ibm_ssh_key)

        if data.get('subnets'):
            for subnet in data['subnets']:
                ibm_subnet = IBMSubnet(subnet['name'], subnet['zone'], subnet['ip_cidr_block'], cloud_id=cloud_id,
                                       region=ibm_vpc_network.region)
                ibm_subnet.ibm_address_prefix = [
                    address_prefix for address_prefix in ibm_vpc_network.address_prefixes.all() if
                    address_prefix.name == subnet['address_prefix']][0]

                if subnet.get('network_acl'):
                    ibm_subnet.network_acl = \
                        [obj for obj in objs_to_configure if obj.name == subnet['network_acl']['name'] and
                         get_obj_type(obj) == IBMNetworkAcl.__name__][0]

                if subnet.get('public_gateway'):
                    ibm_subnet.ibm_public_gateway = [
                        public_gateway for public_gateway in ibm_vpc_network.public_gateways.all() if
                        public_gateway.name == subnet['public_gateway']][0]

                ibm_vpc_network.subnets.append(ibm_subnet)
                objs_to_configure.append(ibm_subnet)

        if data.get('security_groups'):
            for security_group in data['security_groups']:
                ibm_security_group = IBMSecurityGroup(name=security_group['name'], region=ibm_vpc_network.region)
                for rule in security_group['rules']:
                    ibm_security_group_rule = IBMSecurityGroupRule(
                        rule['direction'], rule['protocol'], rule.get('code'), rule.get('type'), rule.get('port_min'),
                        rule.get('port_max'), rule.get('address'), rule.get('cidr_block'))

                    if rule.get('security_group'):
                        ibm_security_group_rule.rule_type = "security-group"

                    ibm_security_group.rules.append(ibm_security_group_rule)

                ibm_security_group.ibm_vpc_network = ibm_vpc_network
                ibm_security_group.ibm_resource_group = existing_resource_group[0]

        ssh_keys_to_configure = list()
        if data.get('instances'):
            for instance in data['instances']:
                existing_instance = ibm_manager.rias_ops.fetch_ops.get_all_instances(instance['name'])
                if existing_instance:
                    raise IBMInvalidRequestError("IBM VSI with name '{}' already configured".format(instance['name']))

                instance_profile = ibm_manager.rias_ops.fetch_ops.get_all_instance_profiles(
                    instance['instance_profile'])
                if not instance_profile:
                    raise IBMInvalidRequestError(
                        "IBM Instance Profile '{}' not found".format(instance['instance_profile']))

                existing_image = ibm_manager.rias_ops.fetch_ops.get_all_images(instance['image'])
                if not existing_image:
                    raise IBMInvalidRequestError("IBM Image with name '{}' not found".format(instance['image']))

                ibm_instance = IBMInstance(
                    name=instance['name'], zone=instance['zone'], user_data=instance.get('user_data'),
                    cloud_id=cloud_id, region=region)

                ssh_keys = list()
                if instance.get('ssh_keys'):
                    ibm_ssh_key = None
                    for ssh_key in instance['ssh_keys']:
                        for ssh_key_ in ssh_keys_to_configure:
                            if ssh_key_.public_key == ssh_key['public_key']:
                                ibm_ssh_key = ssh_key_
                                break

                        if not ibm_ssh_key:
                            existing_ssh_key = ibm_manager.rias_ops.fetch_ops.get_all_ssh_keys(
                                public_key=ssh_key['public_key'])
                            if existing_ssh_key:
                                ibm_ssh_key = existing_ssh_key[0]
                            else:
                                ssh_key_name = ibm_manager.rias_ops.fetch_ops.get_available_ssh_key_name()
                                ibm_ssh_key = IBMSshKey(
                                    ssh_key_name, "rsa", ssh_key['public_key'], ibm_vpc_network.region,
                                    cloud_id=cloud_id)
                                objs_to_configure.append(ibm_ssh_key)
                                ssh_keys_to_configure.append(ibm_ssh_key)

                        ibm_instance.ssh_keys.append(ibm_ssh_key)
                        ssh_keys.append(ibm_ssh_key)
                        ibm_instance.ssh_keys = ssh_keys

                floating_ips_to_add = list()
                network_interfaces_to_add = list()
                if instance.get('network_interfaces'):
                    interface_count = 0
                    is_primary = True
                    for interface in instance['network_interfaces']:
                        ibm_network_interface = IBMNetworkInterface(
                            NETWORK_INTERFACE_NAME.format(name, interface_count), is_primary)
                        interface_count = interface_count + 1
                        is_primary = False

                        ibm_network_interface.ibm_subnet = [
                            subnet_ for subnet_ in ibm_vpc_network.subnets.all() if
                            subnet_.name == interface['subnet']][0].make_copy()

                        if interface.get('security_groups'):
                            for sec_group in interface['security_groups']:
                                ibm_network_interface.security_group = [
                                    sec_group_ for sec_group_ in ibm_vpc_network.security_groups.all() if
                                    sec_group_.name == sec_group][0].make_copy()

                        if interface.get('reserve_floating_ip'):
                            floating_ip_name = ibm_manager.rias_ops.fetch_ops.get_available_floating_ip_name()
                            ibm_floating_ip = IBMFloatingIP(
                                floating_ip_name, ibm_vpc_network.region, ibm_instance.zone, cloud_id=cloud_id)
                            ibm_network_interface.floating_ip = ibm_floating_ip
                            floating_ips_to_add.append(ibm_floating_ip)
                        network_interfaces_to_add.append(ibm_network_interface)

                volume_attachments = list()
                if instance.get('volume_attachments'):
                    for volume_attachment in instance['volume_attachments']:
                        ibm_boot_volume_attachment = IBMVolumeAttachment(
                            volume_attachment['name'], type_="data", is_delete=volume_attachment['auto_delete'])
                        volume_profile = ibm_manager.rias_ops.fetch_ops.get_all_volume_profiles(
                            volume_attachment['volume_profile_name'])
                        ibm_volume = IBMVolume(
                            name=volume_attachment['name'], capacity=volume_attachment['capacity'],
                            zone=instance['zone'], encryption="provider_managed", cloud_id=cloud_id, region=region)
                        ibm_volume.volume_profile = volume_profile[0]
                        ibm_boot_volume_attachment.volume = ibm_volume
                        volume_attachments.append(ibm_boot_volume_attachment)

                volume_profile = ibm_manager.rias_ops.fetch_ops.get_all_volume_profiles(name="general-purpose")
                ibm_volume = IBMVolume(
                    name=VOLUME_NAME.format(instance['name']), capacity=100, zone=instance['zone'], iops=3000,
                    encryption="provider_managed", region=region, cloud_id=cloud_id)
                ibm_boot_volume_attachment = IBMVolumeAttachment(
                    VOLUME_ATTACHMENT_NAME.format(instance['name']), type_="boot", is_delete=True)
                ibm_volume.volume_profile = volume_profile[0]
                ibm_boot_volume_attachment.volume = ibm_volume
                volume_attachments.append(ibm_boot_volume_attachment)

                ibm_instance.ibm_image = existing_image[0]
                ibm_instance.ibm_resource_group = ibm_vpc_network.ibm_resource_group
                ibm_instance.ibm_instance_profile = instance_profile[0]
                ibm_instance.network_interfaces = network_interfaces_to_add
                ibm_instance.volume_attachments = volume_attachments
                ibm_instance.ssh_keys = ssh_keys
                ibm_instance.ibm_vpc_network = ibm_vpc_network
                objs_to_configure.append(ibm_instance)
                objs_to_configure.extend(floating_ips_to_add)

        if data.get('load_balancers'):
            for load_balancer in data['load_balancers']:
                existing_load_balancer = ibm_manager.rias_ops.fetch_ops.get_all_load_balancers(
                    name=load_balancer["name"])
                if existing_load_balancer:
                    raise IBMInvalidRequestError(
                        "IBM Load Balancer with name '{}' already configured".format(load_balancer["name"]))

                ibm_load_balancer = IBMLoadBalancer(
                    load_balancer['name'], load_balancer['is_public'], data['region'], cloud_id=cloud_id)
                subnets_list = list()
                for subnet in load_balancer['subnets']:
                    ibm_subnet = [subnet_ for subnet_ in ibm_vpc_network.subnets.all() if
                                  subnet_.name == subnet][0]
                    subnets_list.append(ibm_subnet)

                pools_list = list()
                if data.get('pools'):
                    for pool in load_balancer['pools']:
                        ibm_pool = IBMPool(
                            pool['name'], pool['algorithm'], pool['protocol'], pool.get('session_persistence'))
                        if pool.get('health_monitor'):
                            health_check = pool['health_monitor']
                            ibm_health_check = IBMHealthCheck(
                                health_check.get('delay'), health_check.get('max_retries'), health_check.get('timeout'),
                                health_check.get('protocol'), health_check.get('url_path'), health_check.get('port'))
                            ibm_pool.health_check = ibm_health_check

                        if pool.get('members'):
                            for member in pool['members']:
                                ibm_pool_member = IBMPoolMember(member.get('port'), member.get('weight'))
                                ibm_pool_member.instance = \
                                    [instance_ for instance_ in ibm_vpc_network.instances.all() if
                                     instance_.name == member['instance']][0]
                                ibm_pool.pool_members.append(ibm_pool_member)
                        pools_list.append(ibm_pool)

                listeners_list = list()
                if data.get('listeners'):
                    for listener in load_balancer['listeners']:
                        ibm_listener = IBMListener(
                            listener['port'], listener['protocol'], listener.get('connection_limit'))
                        if listener.get('default_pool'):
                            for pool in pools_list:
                                if pool.name == listener['default_pool']:
                                    ibm_listener.ibm_pool = pool
                                    break

                        listeners_list.append(ibm_listener)

                ibm_load_balancer.subnets = subnets_list
                ibm_load_balancer.pools = pools_list
                ibm_load_balancer.listeners = listeners_list
                ibm_load_balancer.ibm_resource_group = ibm_vpc_network.ibm_resource_group
                ibm_vpc_network.load_balancers.append(ibm_load_balancer)
                objs_to_configure.append(ibm_load_balancer)

        ike_policies_to_configure, ipsec_policies_to_configure = list(), list()
        if data.get('ike_policies'):
            for ike_policy in data['ike_policies']:
                ibm_ike_policy = IBMIKEPolicy(
                    ike_policy['name'], data['region'], ike_policy['key_lifetime'],
                    authentication_algorithm=ike_policy['authentication_algorithm'],
                    encryption_algorithm=ike_policy['encryption_algorithm'], ike_version=ike_policy['ike_version'],
                    dh_group=ike_policy['dh_group'])
                ike_policies_to_configure.append(ibm_ike_policy)

        if data.get('ipsec_policies'):
            for ipsec_policy in data['ipsec_policies']:
                ibm_ipsec_policy = IBMIPSecPolicy(
                    ipsec_policy['name'], data['region'], data['key_lifetime'],
                    authentication_algorithm=data['authentication_algorithm'],
                    encryption_algorithm=data['encryption_algorithm'], pfs_dh_group=data['pfs'])
                ipsec_policies_to_configure.append(ibm_ipsec_policy)

        if data.get('vpns'):
            for vpn in data['vpns']:
                ibm_vpn_gateway = IBMVpnGateway(vpn['name'], region=data['region'], cloud_id=cloud_id)
                for connection in vpn['connections']:
                    ibm_vpn_connection = IBMVpnConnection(
                        connection['name'], connection['peer_address'], connection['pre_shared_secret'],
                        json.dumps(connection['local_cidrs']), json.dumps(connection['peer_cidrs']),
                        connection['dead_peer_detection'].get('interval'),
                        connection['dead_peer_detection'].get('timeout'),
                        dpd_action=connection['dead_peer_detection'].get('action'))

                    if connection.get('ike_policy'):
                        ibm_ike_policy = [ike_policy for ike_policy in ike_policies_to_configure if
                                          ike_policy.name == connection['ike_policy']][0]
                        ibm_vpn_connection.ibm_ike_policy = ibm_ike_policy

                    if connection.get('ipsec_policy'):
                        ibm_ipsec_policy = [ipsec_policy for ipsec_policy in ipsec_policies_to_configure if
                                            ipsec_policy.name == connection['ipsec_policy']][0]
                        ibm_vpn_connection.ibm_ipsec_policy = ibm_ipsec_policy

                    ibm_vpn_gateway.vpn_connections.append(ibm_vpn_connection)

                ibm_vpn_gateway.ibm_vpc_network = ibm_vpc_network
                ibm_vpn_gateway.ibm_subnet = \
                    [subnet for subnet in ibm_vpc_network.subnets.all() if subnet.name == vpn['subnet']][0]
                ibm_vpn_gateway.ibm_resource_group = existing_resource_group[0]

        ibm_vpc_network.add_update_db()

        for obj in objs_to_configure:
            configure_and_save_obj_confs(ibm_manager, obj)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            cloud.status = INVALID
        for obj in objs_to_configure:
            if obj.status == CREATING:
                obj.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_vpc_network.status = CREATED
        doosradb.session.commit()

    return ibm_vpc_network


def delete_ibm_vpc(ibm_vpc):
    """
    Delete VPC on IBM cloud. A VPC is a virtual network that belongs to an account and
    provides logical isolation from other networks. A VPC is made up of resources in one
    or more zones. VPCs are global, and each can contain resources in zones from any region.
    :return:
    """
    objs_to_delete = list()

    if not ibm_vpc:
        return

    current_app.logger.info("Deleting VPC '{name}' on IBM Cloud".format(name=ibm_vpc.name))
    try:
        ibm_manager = IBMManager(ibm_vpc.ibm_cloud, ibm_vpc.region)
        for instance in ibm_vpc.instances.all():
            for network_interface in instance.network_interfaces.all():
                if network_interface.floating_ip:
                    floating_ip = ibm_manager.rias_ops.fetch_ops.get_all_floating_ips(
                        network_interface.floating_ip.name)

                    if floating_ip:
                        network_interface.floating_ip.status = DELETING
                        objs_to_delete.append(floating_ip[0])

            existing_instance = ibm_manager.rias_ops.fetch_ops.get_all_instances(instance.name)
            if existing_instance:
                instance.status = DELETING
                objs_to_delete.append(existing_instance[0])

        for security_group in ibm_vpc.security_groups.all():
            if security_group.is_default:
                continue

            existing_sec_group = ibm_manager.rias_ops.fetch_ops.get_all_security_groups(security_group.name)
            if existing_sec_group:
                security_group.status = DELETING
                objs_to_delete.append(existing_sec_group[0])

        for subnet in ibm_vpc.subnets.all():
            existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(subnet.name, subnet.zone, ibm_vpc.name)
            if existing_subnet:
                subnet.status = DELETING
                objs_to_delete.append(existing_subnet[0])

        for public_gateway in ibm_vpc.public_gateways.all():
            existing_pbgw = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
                public_gateway.name, public_gateway.zone, ibm_vpc.name)
            if existing_pbgw:
                public_gateway.status = DELETING
                objs_to_delete.append(existing_pbgw[0])

        existing_vpc = ibm_manager.rias_ops.fetch_ops.get_all_vpcs(name=ibm_vpc.name)
        if existing_vpc:
            ibm_vpc.status = DELETING
            objs_to_delete.append(existing_vpc[0])

        doosradb.session.commit()

        for obj in objs_to_delete:
            if GENERATION == "2" and isinstance(obj, IBMInstance):
                ibm_manager.rias_ops.stop_instance(obj)
            ibm_manager.rias_ops.push_obj_confs(obj, delete=True)
            obj.status = DELETED
            doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_vpc.ibm_cloud.status = INVALID
        for obj in objs_to_delete:
            if not obj.status == DELETED:
                obj.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        doosradb.session.delete(ibm_vpc)
        doosradb.session.commit()
        return True


def configure_ibm_subnet(subnet_name, vpc, data):
    """
    This request creates a new subnet from a subnet template.
    :return:
    """
    ibm_subnet, objs_to_configure, objs_to_update = None, list(), list()
    current_app.logger.info("Deploying Subnet '{name}' on IBM Cloud".format(name=subnet_name))
    try:
        ibm_manager = IBMManager(vpc.ibm_cloud, vpc.region)
        existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(name=subnet_name, zone=data['zone'],
                                                                         vpc=vpc.name)
        if existing_subnet:
            raise IBMInvalidRequestError(
                "IBM Subnet with name '{name}' already exists in this region".format(name=subnet_name))

        existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(
            zone=data['zone'], ip_range=data['ip_cidr_block'])
        if existing_subnet:
            raise IBMInvalidRequestError(
                "IBM Subnet with IP range '{range}' already exists in this region".format(range=data['ip_cidr_block']))

        address_prefix_range_list = ibm_manager.rias_ops.fetch_ops.get_all_vpc_address_prefixes(
            vpc.resource_id, zone=data['zone'])

        is_valid = False
        for address in address_prefix_range_list:
            if validate_ip_in_range(data['ip_cidr_block'], address.address):
                is_valid = True
                break

        if not is_valid:
            raise IBMInvalidRequestError("Invalid IP range {} specified for subnet".format(data['ip_cidr_block']))

        ibm_subnet = IBMSubnet(name=subnet_name, zone=data['zone'], ipv4_cidr_block=data['ip_cidr_block'],
                               cloud_id=vpc.ibm_cloud.id, region=vpc.region)
        ibm_subnet.ibm_vpc_network = vpc
        acl = [acl for acl in vpc.acls.all() if acl.is_default]
        if acl:
            ibm_subnet.network_acl = acl[0]

        ibm_subnet.address_prefix_id = data["address_prefix"]

        ibm_resource_group = IBMResourceGroup(name=data["resource_group"], cloud_id=vpc.ibm_cloud.id)
        ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
        ibm_subnet.ibm_resource_group = ibm_resource_group

        doosradb.session.add(ibm_subnet)
        doosradb.session.commit()

        if data.get('public_gateway'):
            existing_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
                zone=ibm_subnet.zone, vpc_name=vpc.name)
            if existing_public_gateway:
                ibm_public_gateway = existing_public_gateway[0]
            else:
                ibm_public_gateway = IBMPublicGateway(
                    name=PUBLIC_GATEWAY_NAME.format(ibm_subnet.zone), zone=ibm_subnet.zone, region=vpc.region)
                ibm_resource_group = IBMResourceGroup(name=data["resource_group"], cloud_id=vpc.ibm_cloud.id)
                ibm_resource_group = ibm_resource_group.get_existing_from_db() or ibm_resource_group
                ibm_public_gateway.ibm_resource_group = ibm_resource_group
                ibm_public_gateway.ibm_cloud = vpc.ibm_cloud
                ibm_public_gateway.ibm_vpc_network = vpc
                doosradb.session.commit()
                objs_to_configure.append(ibm_public_gateway)

            ibm_public_gateway_db = doosradb.session.query(IBMPublicGateway).filter_by(
                name=ibm_public_gateway.name, vpc_id=ibm_subnet.ibm_vpc_network.id, zone=ibm_subnet.zone).first()

            if not ibm_public_gateway_db:
                ibm_public_gateway.ibm_cloud = vpc.ibm_cloud
                ibm_public_gateway.ibm_vpc_network = vpc
                doosradb.session.add(ibm_public_gateway)
                doosradb.session.commit()
        for obj in objs_to_configure:
            if not obj.vpc_id:
                obj.ibm_vpc_network = vpc
                doosradb.session.commit()
            ibm_manager.rias_ops.push_obj_confs(obj)
            obj.status = CREATED
            doosradb.session.commit()

        for obj in objs_to_configure:
            if obj.__class__.__name__ == IBMPublicGateway.__name__:
                configured_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
                    name=obj.name, zone=obj.zone, vpc_name=vpc.name)
                if configured_public_gateway:
                    obj.resource_id = configured_public_gateway[0].resource_id
                    floating_ip_copy = configured_public_gateway[0].floating_ip.make_copy()
                    floating_ip_copy.ibm_cloud = vpc.ibm_cloud
                    obj.floating_ip = floating_ip_copy
                    obj.status = CREATED
                    ibm_subnet.public_gateway_id = ibm_public_gateway.id
                    doosradb.session.commit()

        ibm_manager.rias_ops.create_subnet(ibm_subnet)
        existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(ibm_subnet.name, ibm_subnet.zone, vpc.name)
        if existing_subnet:
            ibm_subnet.resource_id = existing_subnet[0].resource_id
            doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            vpc.ibm_cloud.status = INVALID
        if ibm_subnet:
            ibm_subnet.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_subnet.status = CREATED
        doosradb.session.commit()
    return ibm_subnet


def delete_ibm_subnet(subnet):
    """
    Delete subnet on IBM cloud.
    :return:
    """
    current_app.logger.info("Deleting subnet '{name}' on IBM Cloud".format(name=subnet.name))
    try:
        ibm_manager = IBMManager(subnet.ibm_vpc_network.ibm_cloud, subnet.ibm_vpc_network.region)
        existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(subnet.name, subnet.zone,
                                                                         subnet.ibm_vpc_network.name)
        if existing_subnet:
            subnet.status = DELETING
            doosradb.session.commit()
            ibm_manager.rias_ops.delete_subnet(existing_subnet[0])
        subnet.status = DELETED
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            subnet.ibm_vpc_network.cloud.status = INVALID
        subnet.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        subnet.status = DELETED
        doosradb.session.delete(subnet)
        doosradb.session.commit()
        return True


def attach_public_gateway(subnet):
    """
    This request attaches the network ACL, specified in the request body, to the subnet specified by
    the subnet identifier in the URL. This replaces the existing network ACL on the subnet.
    :return:
    """
    configure_public_gateway = False
    current_app.logger.info("Attaching Public Gateway for Subnet '{name}' on IBM Cloud".format(name=subnet.name))
    try:
        ibm_manager = IBMManager(subnet.ibm_vpc_network.ibm_cloud, subnet.ibm_vpc_network.region)
        existing_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
            zone=subnet.zone, vpc_name=subnet.ibm_vpc_network.name)
        if existing_public_gateway:
            ibm_public_gateway = existing_public_gateway[0]
        else:
            ibm_public_gateway = IBMPublicGateway(
                name=PUBLIC_GATEWAY_NAME.format(subnet.zone), zone=subnet.zone, region=subnet.ibm_vpc_network.region)
            configure_public_gateway = True

        ibm_public_gateway_db = doosradb.session.query(IBMPublicGateway).filter_by(
            name=ibm_public_gateway.name, vpc_id=subnet.ibm_vpc_network.id, zone=subnet.zone).first()
        if not ibm_public_gateway_db:
            ibm_public_gateway.ibm_cloud = subnet.ibm_vpc_network.ibm_cloud
            ibm_public_gateway.ibm_vpc_network = subnet.ibm_vpc_network
            doosradb.session.add(ibm_public_gateway)
            doosradb.session.commit()
        else:
            ibm_public_gateway = ibm_public_gateway_db

        if configure_public_gateway:
            ibm_manager.rias_ops.create_public_gateway(ibm_public_gateway)
            configured_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
                name=ibm_public_gateway.name, zone=ibm_public_gateway.zone, vpc_name=subnet.ibm_vpc_network.name)
            if configured_public_gateway:
                ibm_public_gateway.resource_id = configured_public_gateway[0].resource_id
                floating_ip_copy = configured_public_gateway[0].floating_ip.make_copy()
                floating_ip_copy.ibm_cloud = subnet.ibm_vpc_network.ibm_cloud
                ibm_public_gateway.floating_ip = floating_ip_copy
                ibm_public_gateway.status = CREATED
                doosradb.session.commit()

        ibm_public_gateway.subnets.append(subnet)
        doosradb.session.commit()
        ibm_manager.rias_ops.attach_public_gateway_to_subnet(subnet)

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            subnet.ibm_vpc_network.cloud.status = INVALID
            doosradb.session.commit()
    else:
        return True


def detach_public_gateway(subnet):
    """
    This request detaches the public gateway from the subnet specified by the subnet identifier in the URL.
    :return:
    """
    current_app.logger.info("Detaching Public Gateway for Subnet '{name}' on IBM Cloud".format(name=subnet.name))
    try:
        ibm_manager = IBMManager(subnet.ibm_vpc_network.ibm_cloud, subnet.ibm_vpc_network.region)
        existing_public_gateway = ibm_manager.rias_ops.fetch_ops.get_all_public_gateways(
            name=subnet.ibm_public_gateway.name, zone=subnet.zone, vpc_name=subnet.ibm_vpc_network.name)
        if existing_public_gateway:
            existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(subnet.name, subnet.zone,
                                                                             subnet.ibm_vpc_network.name)
            if existing_subnet:
                ibm_manager.rias_ops.detach_public_gateway_to_subnet(existing_subnet[0])
        subnet.ibm_public_gateway = None
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            subnet.ibm_vpc_network.cloud.status = INVALID
            doosradb.session.commit()
    else:
        return True


def attach_network_acl(subnet, acl_id):
    """
    This request attaches the network ACL, specified in the request body, to the subnet specified by the
    subnet identifier in the URL. This replaces the existing network ACL on the subnet.
    :return:
    """
    network_acl = IBMNetworkAcl.query.get(acl_id)
    if not network_acl:
        return

    current_app.logger.info("Attaching Network ACL for Subnet '{name}' on IBM Cloud".format(name=subnet.name))
    try:
        ibm_manager = IBMManager(subnet.ibm_vpc_network.ibm_cloud, subnet.ibm_vpc_network.region)
        existing_acl = ibm_manager.rias_ops.fetch_ops.get_all_networks_acls(name=network_acl.name)
        if not existing_acl:
            raise IBMInvalidRequestError("Network ACL with name '{name}' doesn't exist".format(name=network_acl.name))

        existing_subnet = ibm_manager.rias_ops.fetch_ops.get_all_subnets(name=subnet.name, zone=subnet.zone,
                                                                         vpc=subnet.ibm_vpc_network.name)
        if not existing_subnet:
            raise IBMInvalidRequestError("Subnet with name '{name}' doesn't exist".format(name=subnet.name))

        subnet.network_acl = network_acl
        doosradb.session.commit()
        ibm_manager.rias_ops.attach_acl_to_subnet(subnet)
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            subnet.ibm_vpc_network.cloud.status = INVALID
            doosradb.session.commit()
    else:
        return True


def configure_address_prefix(data, vpc_id):
    """
    Configuring IBM VPC address prefix on IBM cloud
    :return:
    """
    vpc = (
        doosradb.session.query(IBMVpcNetwork).filter_by(id=vpc_id).first()
    )
    address_prefix = None
    ibm_cloud = IBMCloud.query.filter_by(id=vpc.cloud_id).first()
    if not ibm_cloud:
        current_app.logger.debug("IBM cloud with ID {} not found".format(vpc.cloud_id))
        return

    current_app.logger.info("Creating address prefix in VPC '{name}' on IBM Cloud".format(name=vpc.name))
    try:
        ibm_manager = IBMManager(ibm_cloud, vpc.region)

        address_prefix = IBMAddressPrefix(name=data.get('name'), zone=data.get('zone'), address=data.get('address'))
        address_prefix.ibm_vpc_network = vpc
        doosradb.session.add(address_prefix)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_address_prefix(address_prefix)

        existing_address_prefix = ibm_manager.rias_ops.fetch_ops.get_all_vpc_address_prefixes(
            vpc.resource_id, name=address_prefix.name)
        if existing_address_prefix:
            existing_address_prefix = existing_address_prefix[0]
            existing_address_prefix.resource_id = existing_address_prefix.resource_id
            doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            vpc.ibm_cloud.status = INVALID
        if address_prefix:
            address_prefix.status = ERROR_CREATING
        doosradb.session.commit()

    else:
        address_prefix.status = CREATED
        doosradb.session.commit()

    return address_prefix


def delete_address_prefix(address_prefix):
    """
    This request deletes a address prefix from IBM cloud
    :return:
    """
    current_app.logger.info("Deleting IBM address prefix '{name}' on IBM Cloud".format(name=address_prefix.name))
    try:
        ibm_manager = IBMManager(address_prefix.ibm_vpc_network.ibm_cloud)
        existing_address_prefix = ibm_manager.rias_ops.fetch_ops.get_all_vpc_address_prefixes(
            vpc_id=address_prefix.ibm_vpc_network,
            name=address_prefix.name)
        if existing_address_prefix:
            ibm_manager.rias_ops.delete_address_prefix(existing_address_prefix[0])

        address_prefix.status = DELETED
        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            address_prefix.ibm_cloud.status = INVALID
        if address_prefix:
            address_prefix.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        address_prefix.status = DELETED
        doosradb.session.delete(address_prefix)
        doosradb.session.commit()
        return True


def configure_ibm_vpc_route(cloud_id, vpc_id, data):
    ibm_vpc_route = None
    cloud = IBMCloud.query.get(cloud_id)
    vpc = IBMVpcNetwork.query.get(vpc_id)
    if not cloud:
        current_app.logger.debug("IBM Cloud with ID '{}' not found".format(cloud_id))
        return

    current_app.logger.info("Deploying Route '{name}' for VPC on IBM Cloud".format(name=data['name']))
    try:
        ibm_manager = IBMManager(cloud, vpc.region)

        existing_route = ibm_manager.rias_ops.fetch_ops.get_all_ibm_vpc_routes(vpc_resource_id=vpc.resource_id,
                                                                               name=data['name'], zone=data['zone'])
        if existing_route:
            raise IBMInvalidRequestError(
                "Route `{name}` for the VPC `{vpc_id}` in the Zone `{zone}`already exists.".format(name=data['name'],
                                                                                                   vpc_id=vpc_id,
                                                                                                   zone=data['zone']))

        ibm_vpc_route = IBMVpcRoute(name=data['name'], region=data['region'], zone=data['zone'],
                                    next_hop_address=data['next_hop_address'], destination=data['destination'],
                                    cloud_id=cloud_id, vpc_id=vpc_id)

        ibm_vpc_route.ibm_cloud = cloud
        ibm_vpc_route.ibm_vpc_network = vpc
        doosradb.session.add(ibm_vpc_route)
        doosradb.session.commit()

        ibm_manager.rias_ops.create_ibm_vpc_route(vpc_route_obj=ibm_vpc_route)

        configured_vpc_route = ibm_manager.rias_ops.fetch_ops.get_all_ibm_vpc_routes(vpc_resource_id=vpc.resource_id,
                                                                                     name=data['name'],
                                                                                     zone=data['zone'])

        if not configured_vpc_route:
            raise IBMInvalidRequestError(
                "Failed to configure Route `{name}` in the Zone `{zone_name}` for the VPC ID `{vpc_id}`".format(
                    name=data['name'], zone_name=data['zone'], vpc_id=vpc_id))

        configured_vpc_route = configured_vpc_route[0]
        ibm_vpc_route.resource_id = configured_vpc_route.resource_id
        ibm_vpc_route.created_at = configured_vpc_route.created_at
        ibm_vpc_route.lifecycle_state = configured_vpc_route.lifecycle_state

        doosradb.session.commit()

    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_vpc_route.ibm_cloud.status = INVALID
        if ibm_vpc_route:
            ibm_vpc_route.status = ERROR_CREATING
        doosradb.session.commit()
    else:
        ibm_vpc_route.status = CREATED
        doosradb.session.commit()
    return ibm_vpc_route


def delete_ibm_vpc_route(ibm_vpc_route):
    """
    Delete VPC Route on IBM cloud.
    :return:
    """
    current_app.logger.info("Deleting VPC '{name}' on IBM Cloud".format(name=ibm_vpc_route.name))
    try:
        ibm_manager = IBMManager(ibm_vpc_route.ibm_cloud, ibm_vpc_route.region)
        existing_vpc_route = ibm_manager.rias_ops.fetch_ops.get_all_ibm_vpc_routes(
            vpc_resource_id=ibm_vpc_route.ibm_vpc_network.resource_id, name=ibm_vpc_route.name, zone=ibm_vpc_route.zone)
        if existing_vpc_route:
            ibm_vpc_route.status = DELETING
            doosradb.session.commit()
            ibm_manager.rias_ops.push_obj_confs(existing_vpc_route[0], delete=True)
        existing_vpc_route[0].lifecycle_state = DELETED
        doosradb.session.commit()
    except (IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError) as ex:
        current_app.logger.info(ex)
        if isinstance(ex, IBMAuthError):
            ibm_vpc_route.ibm_vpc_network.cloud.status = INVALID
        ibm_vpc_route.status = ERROR_DELETING
        doosradb.session.commit()
    else:
        ibm_vpc_route.status = DELETED
        doosradb.session.delete(ibm_vpc_route)
        doosradb.session.commit()
        return True
