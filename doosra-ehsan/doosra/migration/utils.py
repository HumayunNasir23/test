from flask import current_app

from doosra.migration.analyzers.vyatta_5600_analyzer.vyatta_5600_analyzer import Vyatta56Analyzer
from doosra.migration.consts import IBM_CLOUD
from doosra.migration.managers.exceptions import *
from doosra.migration.managers.softlayer_manager import SoftLayerManager
from doosra.models import IBMAddressPrefix, IBMDedicatedHost, IBMVpcNetwork, IBMPublicGateway


def migrate_vpc_configs(configs=None, user_name=None, api_key=None, cloud_type="IBM"):
    """
    This method migrate configs from a given VRA file, organize those objects into buckets,
    and then transforms to VPC schema
    :return:
    """
    vpc_data = dict()
    if user_name and api_key:
        try:
            current_app.logger.info(
                "Starting Softlayer discovery for username '{user_name}'".format(user_name=user_name))

            softlayer_manager = SoftLayerManager(user_name, api_key)
            vpc_data['subnets'] = softlayer_manager.fetch_ops.list_private_subnets()
            vpc_data['security_groups'] = softlayer_manager.fetch_ops.list_security_groups()
            vpc_data['instances'] = softlayer_manager.fetch_ops.list_virtual_servers(subnets=vpc_data["subnets"])
            vpc_data['load_balancers'] = softlayer_manager.fetch_ops.list_load_balancers(vpc_data['instances'])
            vpc_data['dedicated_hosts'] = softlayer_manager.fetch_ops.list_dedicated_hosts()
            vpc_data['kubernetes_clusters'] = softlayer_manager.fetch_ops.list_kubernetes_clusters(user_name, api_key)

        except (SLAuthError, SLExecuteError, SLInvalidRequestError) as ex:
            current_app.logger.info(ex)
            return

    if configs:
        current_app.logger.info("Starting VRA discovery for VYATTA-5600 Config File")
        vy56_analyser = Vyatta56Analyzer(configs)
        vpc_data['firewalls'] = list()
        if not vpc_data.get('subnets'):
            vpc_data['subnets'] = vy56_analyser.get_private_subnets()
        else:
            for subnet in vpc_data['subnets']:
                subnet.public_gateway = vy56_analyser.has_public_gateway(subnet.network)
                subnet.firewalls = vy56_analyser.get_attached_firewalls(subnet.vif_id)

        vpc_data['vpns'] = vy56_analyser.get_ipsec()
        for subnet in vpc_data['subnets']:
            vpc_data['firewalls'].extend(subnet.firewalls)

    if cloud_type == IBM_CLOUD:
        current_app.logger.info("Softlayer Discovery completed for cloud_type '{}'".format(cloud_type))
        return {"ported_schema": generate_ibm_vpc_schema(vpc_data), "discovered_schema": get_softlayer_schema(vpc_data)}


def generate_ibm_vpc_schema(data):
    """
    This methods generates an equivalent VPC schema for IBM, the following assumptions are made when migrating:
    1) {name, region, zone} are defined as 'dummy'
    2) Only one Public Gateways can be attached to a given zone in IBM
    3) One Vyatta is treated as a single VPC in IBM
    :return:
    """
    ibm_vpc_network = IBMVpcNetwork(name="wip-template", region="dummy-region", address_prefix_management='manual')
    ibm_public_gateway = IBMPublicGateway(name="dummy-zone-pbgw", zone="dummy-zone", region="dummy-region")

    if not data['subnets']:
        return

    address_prefixes_list = list()
    for subnet in data['subnets']:
        ibm_subnet = subnet.to_ibm()

        if ibm_subnet.ipv4_cidr_block in [subnet.ipv4_cidr_block for subnet in ibm_vpc_network.subnets.all()]:
            continue

        for address_prefix in address_prefixes_list:
            if subnet.network == address_prefix.address:
                ibm_subnet.ibm_address_prefix = address_prefix
                break

        if not ibm_subnet.ibm_address_prefix:
            ibm_address_prefix = IBMAddressPrefix(
                name="address-prefix-{}".format(subnet.name), zone="dummy-zone", address=subnet.network)
            ibm_subnet.ibm_address_prefix = ibm_address_prefix
            address_prefixes_list.append(ibm_address_prefix)

        if subnet.public_gateway:
            ibm_subnet.ibm_public_gateway = ibm_public_gateway
            if not ibm_vpc_network.public_gateways.all():
                ibm_vpc_network.public_gateways.append(ibm_public_gateway)

        ibm_vpc_network.subnets.append(ibm_subnet)
        ibm_vpc_network.address_prefixes.append(ibm_subnet.ibm_address_prefix)

    dh_gen2_id_to_classical_id = {}
    dh_classical_id_to_gen2_id = {}
    ibm_dedicated_hosts = list()
    for dedicated_host in data.get("dedicated_hosts", []):
        ibm_dedicated_host = IBMDedicatedHost(name=dedicated_host.name)
        dh_gen2_id_to_classical_id[ibm_dedicated_host.id] = dedicated_host.id
        dh_classical_id_to_gen2_id[dedicated_host.id] = ibm_dedicated_host.id
        ibm_dedicated_hosts.append(ibm_dedicated_host)

    for security_group in data.get("security_groups", []):
        ibm_vpc_network.security_groups.append(security_group.to_ibm())

    for instance in data.get('instances', []):
        ibm_instance = instance.to_ibm()
        if instance.dedicated_host_id:
            for ibm_dedicated_host in ibm_dedicated_hosts:
                if ibm_dedicated_host.id == dh_classical_id_to_gen2_id[instance.dedicated_host_id]:
                    ibm_instance.ibm_dedicated_host = ibm_dedicated_host
                    ibm_dedicated_host.instances.append(ibm_instance)
            print(ibm_instance.ibm_dedicated_host)

        for interface in ibm_instance.network_interfaces.all():
            interface.ibm_subnet = \
                [subnet for subnet in ibm_vpc_network.subnets.all() if subnet.name == interface.ibm_subnet.name][0]

            interface_security_groups = interface.security_groups.all()
            interface.security_groups = list()
            for security_group in interface_security_groups:
                interface.security_groups.append(
                    [security_group_ for security_group_ in ibm_vpc_network.security_groups.all() if
                     security_group.name == security_group_.name][0])

        ibm_vpc_network.instances.append(ibm_instance)

    for lb in data.get('load_balancers', []):
        ibm_load_balancer = lb.to_ibm()
        subnets_to_add = list()
        for subnet in ibm_load_balancer.subnets.all():
            subnets_to_add.append(
                [subnet_ for subnet_ in ibm_vpc_network.subnets.all() if subnet_.name == subnet.name][0])

        for pool in ibm_load_balancer.pools.all():
            for pool_mem in pool.pool_members.all():
                pool_mem.instance = \
                    [instance for instance in ibm_vpc_network.instances.all() if
                     instance.name == pool_mem.instance.name][0]

        ibm_load_balancer.subnets = subnets_to_add
        ibm_vpc_network.load_balancers.append(ibm_load_balancer)

    ike_policies_to_add, ipsec_policies_to_add = list(), list()
    for vpn in data.get('vpns', []):
        ibm_vpn = vpn.to_ibm()
        for connection in ibm_vpn.vpn_connections.all():
            if connection.ibm_ike_policy:
                found = False
                for ike_policy in ike_policies_to_add:
                    if connection.ibm_ike_policy.name == ike_policy.name:
                        connection.ibm_ike_policy = ike_policy
                        found = True
                        break

                if not found:
                    ike_policies_to_add.append(connection.ibm_ike_policy)

            if connection.ibm_ipsec_policy:
                found = False
                for ipsec_policy in ipsec_policies_to_add:
                    if connection.ibm_ipsec_policy.name == ipsec_policy.name:
                        connection.ibm_ipsec_policy = ipsec_policy
                        found = True
                        break

                if not found:
                    ipsec_policies_to_add.append(connection.ibm_ipsec_policy)

        ibm_vpc_network.vpn_gateways.append(ibm_vpn)

    ibm_vpc_network.address_prefixes = address_prefixes_list
    vpc_json = ibm_vpc_network.to_json()

    vpc_json["dedicated_hosts"] = []
    for ibm_dedicated_host in ibm_dedicated_hosts:
        ibm_dh_json = ibm_dedicated_host.to_json()
        ibm_dh_json["classical_dedicated_host_id"] = dh_gen2_id_to_classical_id[ibm_dh_json["id"]]
        vpc_json["dedicated_hosts"].append(ibm_dh_json)

    return vpc_json


def get_softlayer_schema(vpc_data):
    """
    This methods generates an equivalent json schema for softlayer objects
    """
    return {
        "subnets": [subnet.to_json() for subnet in vpc_data['subnets']] if vpc_data.get('subnets') else [],
        "security_groups": [security_group.to_json() for security_group in vpc_data['security_groups']]
        if vpc_data.get('security_groups') else [],
        "firewalls": [firewall.to_firewall_json() for firewall in vpc_data['firewalls']] if vpc_data.get(
            'firewalls') else [],
        "vpns": [vpn.to_json() for vpn in vpc_data['vpns']] if vpc_data.get('vpns') else [],
        "instances": [instance.to_json() for instance in vpc_data['instances']] if vpc_data.get('instances') else [],
        "load_balancers": [load_balancer.to_json() for load_balancer in vpc_data['load_balancers']] if vpc_data.get(
            'load_balancers') else [],
        "dedicated_hosts": [dedicated_host.to_json() for dedicated_host in vpc_data["dedicated_hosts"]],
        "kubernetes_clusters": [kubernetes_cluster.to_json() for kubernetes_cluster in vpc_data['kubernetes_clusters']]
        if vpc_data.get('kubernetes_clusters') else []
    }
