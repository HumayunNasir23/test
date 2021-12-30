import time
from datetime import datetime

from flask import current_app
from requests.exceptions import ConnectionError, ReadTimeout, RequestException
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

from doosra.common.consts import CREATED
from doosra.common.utils import validate_ip_in_range
from doosra.ibm.common.consts import INST_START
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.operations.rias.consts import GENERATION, VERSION
from doosra.ibm.managers.operations.rias.rias_patterns import *
from doosra.models import (
    IBMAddressPrefix,
    IBMCredentials,
    IBMFloatingIP,
    IBMHealthCheck,
    IBMImage,
    IBMInstance,
    IBMInstanceProfile,
    IBMNetworkAcl,
    IBMNetworkAclRule,
    IBMNetworkInterface,
    IBMPool,
    IBMPoolMember,
    IBMPublicGateway,
    IBMSecurityGroup,
    IBMSecurityGroupRule,
    IBMSshKey,
    IBMSubnet,
    IBMVolume,
    IBMVolumeProfile,
    IBMVolumeAttachment,
    IBMVpcNetwork,
    IBMLoadBalancer,
    IBMListener,
    IBMIKEPolicy,
    IBMVpnConnection,
    IBMVpnGateway,
    IBMIPSecPolicy,
    IBMVpcRoute,
    IBMOperatingSystem,
    KubernetesCluster,
    KubernetesClusterWorkerPool,
    KubernetesClusterWorkerPoolZone,
)


class FetchOperations(object):
    def __init__(self, cloud, region, base_url, session, iam_ops, resource_ops, k8s_base_url=None, session_k8s=None):
        self.cloud = cloud
        self.region = region
        self.base_url = base_url
        self.k8s_base_url = k8s_base_url
        self.session = session
        self.session_k8s = session_k8s
        self.iam_ops = iam_ops
        self.resource_ops = resource_ops

    def list_obj_method_mapper(self, obj):
        func_map = {
            IBMAddressPrefix: self.get_all_vpc_address_prefixes,
            IBMFloatingIP: self.get_all_floating_ips,
            IBMInstance: self.get_all_instances,
            IBMSshKey: self.get_all_ssh_keys,
            IBMVpcNetwork: self.get_all_vpcs,
            IBMSubnet: self.get_all_subnets,
            IBMLoadBalancer: self.get_all_load_balancers,
            IBMSecurityGroup: self.get_all_security_groups,
            IBMPublicGateway: self.get_all_public_gateways,
            IBMSecurityGroupRule: self.get_all_security_group_rules,
            IBMNetworkAcl: self.get_all_networks_acls,
            IBMIKEPolicy: self.get_all_ike_policies,
            IBMIPSecPolicy: self.get_all_ipsec_policies,
            IBMVpnConnection: self.get_all_vpn_connections,
            IBMVpnGateway: self.get_all_vpn_gateways,
            IBMImage: self.get_all_images,
            IBMVpcRoute: self.get_all_ibm_vpc_routes,
            KubernetesCluster: self.get_all_k8s_clusters,
            KubernetesClusterWorkerPool: self.get_all_k8s_cluster_worker_pool,
        }

        if obj.__class__.__name__ in [IBMAddressPrefix.__name__, IBMVpcRoute.__name__]:
            return func_map[obj.__class__](obj.ibm_vpc_network.resource_id, obj.name)

        elif obj.__class__.__name__ in [IBMPublicGateway.__name__, IBMSubnet.__name__]:
            return func_map[obj.__class__](obj.name, obj.zone, obj.ibm_vpc_network.name)

        elif obj.__class__.__name__ == IBMSecurityGroupRule.__name__:
            return func_map[obj.__class__](
                obj.security_group.resource_id,
                obj.direction,
                obj.protocol,
                obj.code,
                obj.type,
                obj.port_min,
                obj.port_max,
                obj.address,
                obj.cidr_block,
            )

        elif obj.__class__.__name__ == IBMVpnConnection.__name__:
            return func_map[obj.__class__](obj.ibm_vpn_gateway.resource_id, obj.name)

        elif obj.__class__.__name__ == IBMSecurityGroup.__name__:
            return func_map[obj.__class__](obj.name, obj.ibm_vpc_network.name)

        elif obj.__class__.__name__ == IBMLoadBalancer.__name__:
            return func_map[obj.__class__](obj.name, obj.ibm_vpc_network.name, required_relations=False)
        elif obj.__class__.__name__ == KubernetesCluster.__name__:
            return func_map[obj.__class__](obj.name, obj.ibm_vpc_network)
        elif obj.__class__.__name__ == KubernetesClusterWorkerPool.__name__:
            return func_map[obj.__class__](obj.kubernetes_clusters.resource_id, obj.name, obj.kubernetes_clusters.ibm_vpc_network.region)

        return func_map[obj.__class__](obj.name)

    def get_regions(self):
        """
        Get available regions for IBM cloud
        :return:
        """
        regions_list = list()
        regions = self.execute(self.format_api_url(LIST_REGIONS_PATTERN))
        if regions.get("regions"):
            for region in regions.get("regions"):
                if region.get("status") == "available":
                    regions_list.append(region.get("name"))

        return regions_list

    def get_zones(self):
        """
        Get available zones for IBM cloud
        :return:
        """
        zones_list = list()
        zones = self.execute(
            self.format_api_url(LIST_ZONES_PATTERN, region=self.region)
        )
        if zones.get("zones"):
            for zone in zones.get("zones"):
                if zone.get("status") == "available":
                    zones_list.append(zone.get("name"))
        return zones_list

    def get_all_vpcs(
        self,
        name=None,
        fetch_instances=False,
        fetch_lbs=False,
        fetch_vpns=False,
        required_relations=True,
    ):
        """
        This request lists all VPCs. A VPC is a virtual network that belongs to an account and provides
        logical isolation from other networks. A VPC is made up of resources in one or more zones.
        VPCs are global, and each can contain resources in zones from any region.
        :return:
        """
        vpc_list = list()
        response = self.execute(self.format_api_url(LIST_VPCS_PATTERN))
        if not response.get("vpcs"):
            return vpc_list

        for vpc in response.get("vpcs"):
            ibm_vpc = IBMVpcNetwork(
                name=vpc["name"],
                region=self.region,
                crn=vpc["crn"],
                classic_access=vpc["classic_access"],
                cloud_id=self.cloud.id,
                resource_id=vpc["id"],
                status=CREATED,
            )

            if name and name != ibm_vpc.name:
                continue

            if required_relations:
                resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                    resource_id=vpc["resource_group"]["id"]
                )
                if resource_group:
                    ibm_vpc.ibm_resource_group = resource_group[0]

                default_network_acl = self.get_all_networks_acls(
                    vpc["default_network_acl"]["name"]
                )
                if default_network_acl:
                    default_network_acl = default_network_acl[0]
                    default_network_acl.is_default = True
                    ibm_vpc.acls.append(default_network_acl)

                security_groups = self.get_all_security_groups(vpc=ibm_vpc.name)
                if security_groups:
                    for security_group in security_groups:
                        if (
                            security_group.name
                            == vpc["default_security_group"]["name"]
                        ):
                            security_group.is_default = True

                        ibm_vpc.security_groups.append(security_group)

                subnets = self.get_all_subnets(vpc=ibm_vpc.name)
                if subnets:
                    ibm_vpc.subnets = subnets

                public_gateways = self.get_all_public_gateways(
                    vpc_name=ibm_vpc.name
                )
                if public_gateways:
                    ibm_vpc.public_gateways = public_gateways

                address_prefixes = self.get_all_vpc_address_prefixes(
                    ibm_vpc.resource_id
                )
                if address_prefixes:
                    ibm_vpc.address_prefixes = address_prefixes

                if fetch_instances:
                    ibm_vpc.instances = self.get_all_instances(
                        vpc_name=ibm_vpc.name
                    )

                if fetch_lbs:
                    ibm_vpc.load_balancers = self.get_all_load_balancers(
                        vpc_name=ibm_vpc.name
                    )

                if fetch_vpns:
                    ibm_vpc.vpn_gateways = self.get_all_vpn_gateways(
                        vpc_name=ibm_vpc.name
                    )

            vpc_list.append(ibm_vpc)
        return vpc_list

    def get_vpc_status(self, vpc_id):
        """
        This request retrieves a single VPC specified by the identifier in the URL.
        :return:
        """
        response = self.execute(self.format_api_url(GET_VPC_PATTERN, vpc_id=vpc_id))
        return response.get("status")

    def get_vpc_route_status(self, vpc_route_id):
        """
        This request retrieves a single route specified by the identifier in the URL.
        """
        vpc_route = IBMVpcRoute.query.filter_by(cloud_id=self.cloud.id).first()
        response = self.execute(
            self.format_api_url(
                GET_VPC_ROUTE_PATTERN,
                vpc_id=vpc_route.ibm_vpc_network.resource_id,
                route_id=vpc_route_id,
            )
        )
        return response.get("lifecycle_state")

    def get_vpc_default_security_group(self, vpc_id):
        """
        This request lists the default security group for the VPC specified by the identifier in the URL.
        The default security group is applied to any new network interfaces in the VPC that do not specify
        a security group.
        :param vpc_id:
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_DEFAULT_SECURITY_GROUP_PATTERN, vpc_id=vpc_id)
        )
        security_group = IBMSecurityGroup(
            name=response.get("name", "DEFAULT"),
            resource_id=response["id"],
            is_default=True,
            status=CREATED,
            cloud_id=self.cloud.id,
            region=self.region,
        )
        if response.get("rules"):
            for rule in response["rules"]:
                ibm_rule = IBMSecurityGroupRule(
                    rule["direction"],
                    rule.get("protocol"),
                    rule.get("code"),
                    rule.get("type"),
                    rule.get("port_min"),
                    rule.get("port_max"),
                    rule.get("address"),
                    rule.get("cidr_block"),
                    resource_id=rule.get("id"),
                    status=CREATED,
                )

                if rule.get("remote"):
                    if rule["remote"].get("cidr_block"):
                        ibm_rule.rule_type = "cidr_block"
                        ibm_rule.cidr_block = rule["remote"].get("cidr_block")
                    elif rule["remote"].get("address"):
                        ibm_rule.rule_type = "address"
                        ibm_rule.address = rule["remote"].get("address")
                    elif rule["remote"].get("name"):
                        ibm_rule.rule_type = "security_group"
                security_group.rules.append(ibm_rule)

            resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                resource_id=response["resource_group"]["id"]
            )
            if resource_group:
                security_group.ibm_resource_group = resource_group[0]

            return security_group

    def get_all_networks_acls(self, name=None, vpc=None):
        """
        This request lists all network ACLs in the region.
        :return:
        """
        network_acl_list = list()
        response = self.execute(self.format_api_url(LIST_ACLS_PATTERN))
        if response.get("network_acls"):
            for network_acl in response.get("network_acls"):
                ibm_network_acl = IBMNetworkAcl(
                    network_acl["name"],
                    self.region,
                    network_acl["id"],
                    status=CREATED,
                    cloud_id=self.cloud.id,
                )
                if name and name != ibm_network_acl.name:
                    continue

                if network_acl.get("rules"):
                    for rule in network_acl["rules"]:
                        ibm_network_acl_rule = IBMNetworkAclRule(
                            rule["name"],
                            rule["action"],
                            rule.get("destination"),
                            rule["direction"],
                            rule.get("source"),
                            rule["protocol"],
                            rule.get("destination_port_max"),
                            rule.get("destination_port_min"),
                            rule.get("source_port_max"),
                            rule.get("source_port_min"),
                            rule.get("code"),
                            rule.get("type"),
                            status=CREATED,
                        )
                        ibm_network_acl.rules.append(ibm_network_acl_rule)

                if vpc and vpc != network_acl["vpc"].get("name"):
                    continue

                network_acl_list.append(ibm_network_acl)

        return network_acl_list

    def get_all_network_acl_rules(
        self,
        acl_id,
        name=None,
        action=None,
        destination=None,
        direction=None,
        source=None,
        protocol=None,
        port_max=None,
        port_min=None,
        source_port_max=None,
        source_port_min=None,
        code=None,
        type_=None,
    ):
        """
        This request lists all rules for a network ACL. These rules can allow or deny traffic between a
        source CIDR block and a destination CIDR block over a particular protocol and port range.
        :return:
        """
        network_acl_rules_list = list()
        response = self.execute(
            self.format_api_url(LIST_ACL_RULES_PATTERN, acl_id=acl_id)
        )
        if response.get("rules"):
            for rule in response["rules"]:
                ibm_network_acl_rule = IBMNetworkAclRule(
                    resource_id=rule["id"],
                    name=rule["name"],
                    action=rule["action"],
                    destination=rule.get("destination"),
                    direction=rule["direction"],
                    source=rule.get("source"),
                    protocol=rule["protocol"],
                    port_max=rule.get("port_max"),
                    port_min=rule.get("port_min"),
                    source_port_max=rule.get("source_port_max"),
                    source_port_min=rule.get("source_port_min"),
                    code=rule.get("code"),
                    type_=rule.get("type"),
                    status=CREATED,
                )

                if not (
                    (name and name != ibm_network_acl_rule.name)
                    or (action and action != ibm_network_acl_rule.action)
                    or (destination and destination != ibm_network_acl_rule.destination)
                    or (direction and direction != ibm_network_acl_rule.direction)
                    or (source and source != ibm_network_acl_rule.source)
                    or (protocol and protocol != ibm_network_acl_rule.protocol)
                    or (port_max and port_max != ibm_network_acl_rule.port_max)
                    or (port_min and port_min != ibm_network_acl_rule.port_min)
                    or (
                        source_port_max
                        and source_port_max != ibm_network_acl_rule.source_port_max
                    )
                    or (
                        source_port_min
                        and source_port_min != ibm_network_acl_rule.source_port_min
                    )
                    or (code and code != ibm_network_acl_rule.code)
                    or (type_ and type_ != ibm_network_acl_rule.type)
                ):
                    network_acl_rules_list.append(ibm_network_acl_rule)
        return network_acl_rules_list

    def get_all_security_groups(self, name=None, vpc=None, required_relations=True):
        """
        This request lists all existing security groups. Security groups provide a convenient way to apply IP
        filtering rules to instances in the associated VPC.
        :return:
        """
        security_groups_list = list()
        response = self.execute(self.format_api_url(LIST_SECURITY_GROUPS_PATTERN))
        if response.get("security_groups"):
            for security_group in response["security_groups"]:
                if name and name != security_group["name"]:
                    continue

                if vpc and vpc != security_group["vpc"]["name"]:
                    continue

                ibm_security_group = IBMSecurityGroup(
                    name=security_group["name"],
                    resource_id=security_group["id"],
                    status=CREATED,
                    cloud_id=self.cloud.id,
                    region=self.region,
                )
                if security_group.get("rules"):
                    for rule in security_group["rules"]:
                        ibm_rule = IBMSecurityGroupRule(
                            rule["direction"],
                            rule.get("protocol"),
                            rule.get("code"),
                            rule.get("type"),
                            rule.get("port_min"),
                            rule.get("port_max"),
                            rule.get("address"),
                            rule.get("cidr_block"),
                            resource_id=rule.get("id"),
                            status=CREATED,
                        )
                        if rule.get("remote"):
                            if rule["remote"].get("cidr_block"):
                                ibm_rule.rule_type = "cidr_block"
                                ibm_rule.cidr_block = rule["remote"].get("cidr_block")
                            elif rule["remote"].get("address"):
                                ibm_rule.rule_type = "address"
                                ibm_rule.address = rule["remote"].get("address")
                            elif rule["remote"].get("name"):
                                ibm_rule.rule_type = "security_group"
                        ibm_security_group.rules.append(ibm_rule)

                if required_relations:
                    resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                        resource_id=security_group["resource_group"]["id"]
                    )
                    if resource_group:
                        ibm_security_group.ibm_resource_group = resource_group[0]

                security_groups_list.append(ibm_security_group)
        return security_groups_list

    def get_all_security_group_rules(
        self,
        security_group_id,
        direction=None,
        protocol=None,
        code=None,
        type_=None,
        port_min=None,
        port_max=None,
        address=None,
        cidr_block=None,
        security_group_rule_id=None,
    ):
        """
        This request lists all the security group rules for a particular security group
        :return:
        """
        security_group_rules_list = list()
        response = self.execute(
            self.format_api_url(
                LIST_SECURITY_GROUP_RULES_PATTERN, security_group_id=security_group_id
            )
        )
        if response.get("rules"):
            for rule in response["rules"]:
                ibm_rule = IBMSecurityGroupRule(
                    rule["direction"],
                    rule.get("protocol"),
                    rule.get("code"),
                    rule.get("type"),
                    rule.get("port_min"),
                    rule.get("port_max"),
                    rule.get("address"),
                    rule.get("cidr_block"),
                    resource_id=rule.get("id"),
                    status=CREATED,
                )

                if rule.get("remote"):
                    if rule["remote"].get("cidr_block"):
                        ibm_rule.rule_type = "cidr_block"
                        ibm_rule.cidr_block = rule["remote"].get("cidr_block")

                    elif rule["remote"].get("address"):
                        ibm_rule.rule_type = "address"
                        ibm_rule.address = rule["remote"].get("address")

                    elif rule["remote"].get("name"):
                        ibm_rule.rule_type = "security_group"

                if not (
                    (direction and direction != ibm_rule.direction)
                    or (protocol and protocol != ibm_rule.protocol)
                    or (code and code != ibm_rule.code)
                    or (type_ and type_ != ibm_rule.type)
                    or (port_min and port_min != ibm_rule.port_min)
                    or (port_max and port_max != ibm_rule.port_max)
                    or (address and address != ibm_rule.address)
                    or (cidr_block and cidr_block != ibm_rule.cidr_block)
                    or (
                        security_group_rule_id
                        and security_group_rule_id != ibm_rule.resource_id
                    )
                ):
                    security_group_rules_list.append(ibm_rule)
        return security_group_rules_list

    def get_all_vpc_address_prefixes(
        self, vpc_id, name=None, zone=None, network=None, subnet_ip_range=None
    ):
        """
        This request lists all address pool prefixes for a VPC.
        :return:
        """
        address_prefixes_list = list()
        response = self.execute(
            self.format_api_url(LIST_ADDRESS_PREFIXES_PATTERN, vpc_id=vpc_id)
        )
        if response.get("address_prefixes"):
            for address_prefix in response["address_prefixes"]:
                ibm_address_prefix = IBMAddressPrefix(
                    name=address_prefix["name"],
                    zone=address_prefix["zone"]["name"],
                    address=address_prefix["cidr"],
                    resource_id=address_prefix["id"],
                    status=CREATED,
                    is_default=address_prefix["is_default"],
                )

                if not (
                    (name and name != ibm_address_prefix.name)
                    or (zone and zone != ibm_address_prefix.zone)
                    or (
                        network
                        and network.split("/")[0]
                        != ibm_address_prefix.address.split("/")[0]
                    )
                    or (
                        subnet_ip_range
                        and not validate_ip_in_range(
                            subnet_ip_range, address_prefix["cidr"]
                        )
                    )
                ):
                    address_prefixes_list.append(ibm_address_prefix)

        return address_prefixes_list

    def get_all_subnets(
        self,
        name=None,
        zone=None,
        vpc=None,
        ip_range=None,
        resource_id=None,
        required_relations=True,
    ):
        """
        This request lists all subnets in the region. Subnets are contiguous ranges of IP addresses specified in
         block notation. Each subnet is within a particular zone and cannot span multiple zones or regions.
        :return:
        """
        subnets_list = list()
        response = self.execute(self.format_api_url(LIST_SUBNETS_PATTERN))
        if not response.get("subnets"):
            return subnets_list

        for subnet in response["subnets"]:
            if vpc and vpc != subnet["vpc"]["name"]:
                continue

            ibm_subnet = IBMSubnet(
                name=subnet["name"],
                zone=subnet["zone"]["name"],
                ipv4_cidr_block=subnet["ipv4_cidr_block"],
                resource_id=subnet["id"],
                status=CREATED,
                cloud_id=self.cloud.id,
                region=self.region,
            )
            if required_relations:
                if subnet.get("network_acl"):
                    network_acl = self.get_all_networks_acls(
                        name=subnet["network_acl"].get("name")
                    )
                    if network_acl:
                        ibm_subnet.network_acl = network_acl[0]

                address_prefix = self.get_all_vpc_address_prefixes(
                    subnet_ip_range=subnet["ipv4_cidr_block"],
                    zone=ibm_subnet.zone,
                    vpc_id=subnet["vpc"]["id"],
                )
                if address_prefix:
                    ibm_subnet.ibm_address_prefix = address_prefix[0]

                attached_public_gateway = self.get_attached_public_gateway(
                    ibm_subnet
                )
                if attached_public_gateway:
                    ibm_subnet.ibm_public_gateway = attached_public_gateway

            if not (
                (name and name != ibm_subnet.name)
                or (vpc and vpc != subnet["vpc"]["name"])
                or (zone and zone != ibm_subnet.zone)
                or (ip_range and ip_range != ibm_subnet.ipv4_cidr_block)
                or (resource_id and resource_id != ibm_subnet.resource_id)
            ):
                subnets_list.append(ibm_subnet)

        return subnets_list

    def get_subnet_status(self, subnet_id):
        """
        This request retrieves a single subnet specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_SUBNET_PATTERN, subnet_id=subnet_id)
        )
        return response.get("status")

    def get_all_public_gateways(self, name=None, zone=None, vpc_name=None):
        """
        This request lists all public gateways. A public gateway is a virtual network device associated with a VPC,
        which allows access to the Internet.
        :return:
        """
        public_gateways_list = list()
        response = self.execute(self.format_api_url(LIST_PUBLIC_GATEWAYS_PATTERN))
        if response.get("public_gateways"):
            for public_gateway in response.get("public_gateways"):
                if name and name != public_gateway["name"]:
                    continue

                ibm_public_gateway = IBMPublicGateway(
                    name=public_gateway["name"],
                    zone=public_gateway["zone"]["name"],
                    resource_id=public_gateway["id"],
                    status=CREATED,
                    region=self.region,
                    cloud_id=self.cloud.id,
                )

                if public_gateway.get("floating_ip"):
                    ibm_floating_ip = IBMFloatingIP(
                        name=public_gateway["floating_ip"]["name"],
                        region=self.region,
                        zone=ibm_public_gateway.zone,
                        address=public_gateway["floating_ip"]["address"],
                        resource_id=public_gateway["floating_ip"]["id"],
                        status=CREATED,
                        cloud_id=self.cloud.id,
                    )
                    ibm_public_gateway.floating_ip = ibm_floating_ip

                if not (
                    (name and name != ibm_public_gateway.name)
                    or (vpc_name and vpc_name != public_gateway["vpc"]["name"])
                    or (zone and zone != ibm_public_gateway.zone)
                ):
                    public_gateways_list.append(ibm_public_gateway)

        return public_gateways_list

    def get_public_gateway_status(self, public_gateway_id):
        """
        This request retrieves a single Public Gateway specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_PUBLIC_GATEWAY_PATTERN, public_gateway_id=public_gateway_id
            )
        )
        return response.get("status")

    def get_instance_status(self, instance_id):
        """
        This request retrieves a single instance specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_INSTANCE_PATTERN, instance_id=instance_id)
        )
        return response.get("status")
    
    def get_k8s_cluster_status(self, cluster_id):
        """
        This request retrieves a single k8s cluster specified by the identifier in the URL.
        :return:
        """
        response = self.execute_(self.format_api_url(GET_K8S_CLUSTERS_DETAIL, cluster=cluster_id))
        return response.get("state")

    def get_attached_public_gateway(self, subnet_obj):
        """
        This request retrieves the public gateway attached to the subnet specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_ATTACHED_PUBLIC_GATEWAY_PATTERN, subnet_id=subnet_obj.resource_id
            )
        )
        if not response.get("errors"):
            ibm_public_gateway = IBMPublicGateway(
                name=response["name"],
                zone=response["zone"]["name"],
                resource_id=response["id"],
                status=CREATED,
                region=self.region,
                cloud_id=self.cloud.id,
            )
            if response.get("floating_ip"):
                ibm_floating_ip = IBMFloatingIP(
                    response["floating_ip"]["name"],
                    self.region,
                    ibm_public_gateway.zone,
                    response["floating_ip"]["address"],
                    response["floating_ip"]["id"],
                    CREATED,
                    self.cloud.id,
                )
                ibm_public_gateway.floating_ip = ibm_floating_ip
            return ibm_public_gateway

    def get_all_ike_policies(self, name=None, required_relations=True):
        """
        This request lists all existing IKE Policies.
        :return:
        """
        ike_policies_list = list()
        response = self.execute(self.format_api_url(LIST_IKE_POLICIES))
        if not response.get("ike_policies"):
            return ike_policies_list

        for ike_policy in response["ike_policies"]:
            ibm_ike_policy = IBMIKEPolicy(
                ike_policy["name"],
                self.region,
                ike_policy["key_lifetime"],
                CREATED,
                ike_policy["ike_version"],
                ike_policy["authentication_algorithm"],
                ike_policy["encryption_algorithm"],
                ike_policy["dh_group"],
                ike_policy["id"],
                self.cloud.id,
            )

            if name and name != ike_policy["name"]:
                continue

            if required_relations:
                resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                    resource_id=ike_policy["resource_group"]["id"]
                )
                if resource_group:
                    ibm_ike_policy.ibm_resource_group = resource_group[0]

            ike_policies_list.append(ibm_ike_policy)
        return ike_policies_list

    def get_all_ipsec_policies(self, name=None, required_relations=True):
        """
        This request lists all existing IPsec Policies.
        :return:
        """
        ipsec_policies_list = list()
        response = self.execute(self.format_api_url(LIST_IPSEC_POLICIES))
        if not response.get("ipsec_policies"):
            return ipsec_policies_list

        for ipsec_policy in response["ipsec_policies"]:
            ibm_ipsec_policy = IBMIPSecPolicy(
                ipsec_policy["name"],
                self.region,
                ipsec_policy["key_lifetime"],
                CREATED,
                ipsec_policy["authentication_algorithm"],
                ipsec_policy["encryption_algorithm"],
                ipsec_policy["pfs"],
                ipsec_policy["id"],
                self.cloud.id,
            )

            if name and name != ipsec_policy["name"]:
                continue

            if required_relations:
                resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                    resource_id=ipsec_policy["resource_group"]["id"]
                )
                if resource_group:
                    ibm_ipsec_policy.ibm_resource_group = resource_group[0]

            ipsec_policies_list.append(ibm_ipsec_policy)
        return ipsec_policies_list

    def get_vpn_gateway_status(self, vpn_gateway_id):
        """
        This request retrieves a single VPN Gateway specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_VPN_GATEWAY_PATTERN, vpn_gateway_id=vpn_gateway_id)
        )
        return response.get("status")

    def get_all_vpn_gateways(self, name=None, vpc_name=None, required_relations=True):
        """
        This request lists all VPN gateways. A VPN gateway is a virtual network device associated within VPN Connection.
        :return:
        """
        vpn_gateways_list = list()
        response = self.execute(self.format_api_url(LIST_VPN_GATEWAYS_PATTERN))
        if not response.get("vpn_gateways"):
            return vpn_gateways_list

        for vpn_gateway in response.get("vpn_gateways"):
            ibm_vpn_gateway = IBMVpnGateway(
                name=vpn_gateway["name"],
                region=self.region,
                status=CREATED,
                resource_id=vpn_gateway["id"],
                public_ip=vpn_gateway["public_ip"]["address"],
                created_at=vpn_gateway["created_at"],
                gateway_status=vpn_gateway["status"],
                cloud_id=self.cloud.id,
            )

            if name and name != vpn_gateway["name"]:
                continue

            if required_relations:
                resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                    resource_id=vpn_gateway["resource_group"]["id"]
                )
                if resource_group:
                    ibm_vpn_gateway.ibm_resource_group = resource_group[0]

                connections = self.get_all_vpn_connections(
                    ibm_vpn_gateway.resource_id
                )
                if connections:
                    ibm_vpn_gateway.vpn_connections = connections

            if vpn_gateway.get("subnet"):
                subnet = self.get_all_subnets(
                    name=vpn_gateway["subnet"]["name"],
                    vpc=vpc_name,
                    resource_id=vpn_gateway["subnet"]["id"],
                )
                if subnet:
                    ibm_vpn_gateway.ibm_subnet = subnet[0]

            if vpc_name and not ibm_vpn_gateway.ibm_subnet:
                continue

            vpn_gateways_list.append(ibm_vpn_gateway)
        return vpn_gateways_list

    def get_all_vpn_connections(self, vpn_gateway_id, name=None):
        """
        This request lists all Connections to Specific VPN gateway.
        :return:
        """
        vpn_connection_list = list()
        response = self.execute(
            self.format_api_url(
                LIST_VPN_GATEWAY_CONNECTIONS_PATTERN, vpn_gateway_id=vpn_gateway_id
            )
        )
        if response.get("connections"):
            for connection in response.get("connections"):
                if name and name != connection.get("name"):
                    continue

                ibm_vpn_connection = IBMVpnConnection(
                    connection["name"],
                    connection["peer_address"],
                    connection["psk"],
                    json.dumps(connection["local_cidrs"])
                    if connection.get("local_cidrs")
                    else [],
                    json.dumps(connection["peer_cidrs"])
                    if connection.get("peer_cidrs")
                    else [],
                    connection["dead_peer_detection"]["interval"],
                    connection["dead_peer_detection"]["timeout"],
                    dpd_action=connection["dead_peer_detection"]["action"],
                    resource_id=connection["id"],
                    authentication_mode=connection["authentication_mode"],
                    created_at=connection["created_at"],
                    vpn_status=connection["status"],
                    route_mode=connection["route_mode"],
                )
                vpn_connection_list.append(ibm_vpn_connection)

        return vpn_connection_list

    def get_all_floating_ips(self, name=None):
        """
        This request retrieves all floating IPs in the region. Floating IPs allow inbound and outbound traffic
        from the Internet to an instance.
        :return:
        """
        floating_ips_list = list()
        response = self.execute(self.format_api_url(LIST_FLOATING_IPS_PATTERN))
        if response.get("floating_ips"):
            for floating_ip in response["floating_ips"]:
                ibm_floating_ip = IBMFloatingIP(
                    floating_ip["name"],
                    self.region,
                    floating_ip["zone"]["name"],
                    floating_ip["address"],
                    floating_ip["id"],
                    CREATED,
                    self.cloud.id,
                )

                if name and name != ibm_floating_ip.name:
                    continue

                floating_ips_list.append(ibm_floating_ip)

        return floating_ips_list

    def get_network_interface_floating_ip(self, instance_id, network_interface_id):
        """
        This request lists all floating IPs associated with a network interface.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_INTERFACE_FLOATING_IP_PATTERN,
                instance_id=instance_id,
                network_interface_id=network_interface_id,
            )
        )
        if response.get("floating_ips"):
            floating_ip = response["floating_ips"][0]
            ibm_floating_ip = IBMFloatingIP(
                floating_ip["name"],
                self.region,
                floating_ip["zone"]["name"],
                floating_ip["address"],
                floating_ip["id"],
                CREATED,
                self.cloud.id,
            )
            return ibm_floating_ip

    def get_all_ssh_keys(self, name=None, public_key=None, required_relations=True):
        """
        This request lists all keys. A key contains a public SSH key which may be installed on
        instances when they are created. Private keys are not stored.
        :return:
        """
        ssh_keys_list = list()
        response = self.execute(self.format_api_url(LIST_SSH_KEYS_PATTERN))
        if not response.get("keys"):
            return ssh_keys_list

        for key in response["keys"]:
            ibm_key = IBMSshKey(
                name=key["name"],
                type_=key["type"],
                public_key=key["public_key"],
                region=self.region,
                finger_print=key["fingerprint"],
                status=CREATED,
                resource_id=key["id"],
                cloud_id=self.cloud.id,
            )
            if required_relations:
                if key.get("resource_group"):
                    resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                        resource_id=key["resource_group"]["id"]
                    )
                    if resource_group:
                        ibm_key.ibm_resource_group = resource_group[0]

            if not (
                (name and name != ibm_key.name)
                or (public_key and public_key.strip() != ibm_key.public_key.strip())
            ):
                ssh_keys_list.append(ibm_key)

        return ssh_keys_list

    def get_all_images(self, name=None, visibility=None, status=None, required_relations=True):
        """
        This request lists all images available in the region. An image provides source data for a volume.
        Images are either system-provided, or created from another source, such as importing from object storage.
        :return:
        """
        images_list = list()
        response = self.execute(self.format_api_url(LIST_IMAGES_PATTERN))
        if not response.get("images"):
            return images_list

        for image in response["images"]:
            if status and status != image["status"]:
                continue

            ibm_image = IBMImage(
                name=image["name"], visibility=image["visibility"], resource_id=image["id"], cloud_id=self.cloud.id,
                status=CREATED, region=self.region, size=image["file"].get("size"))

            if name and name != ibm_image.name:
                continue

            if required_relations:
                if image.get("operating_system"):
                    operating_system = self.get_all_operating_systems(name=image["operating_system"]["name"])
                    if operating_system:
                        ibm_image.operating_system = operating_system[0]

                if image.get("resource_group"):
                    resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                        resource_id=image["resource_group"]["id"])
                    if resource_group:
                        ibm_image.ibm_resource_group = resource_group[0]

            if not ((name and name != ibm_image.name) or (visibility and visibility != ibm_image.visibility)):
                images_list.append(ibm_image)

        return images_list

    def get_all_operating_systems(self, name=None, architecture=None):
        """
        This request lists all operating systems available in the region. An operating system provides source data
        for a OS.
        :return:
        """
        operating_systems_list = list()
        response = self.execute(self.format_api_url(LIST_OPERATING_SYSTEMS_PATTERN))

        for operating_system in response.get("operating_systems", []):
            if operating_system["architecture"] == "ppc64le":
                continue
            ibm_operating_system = IBMOperatingSystem(
                name=operating_system["name"],
                architecture="power" if operating_system["architecture"] == "ppc64le" else operating_system[
                    "architecture"],
                family=operating_system["family"], vendor=operating_system["vendor"],
                version=operating_system["version"], cloud_id=self.cloud.id)

            if not ((name and name != ibm_operating_system.name) or
                    (architecture and architecture != ibm_operating_system.architecture)):
                operating_systems_list.append(ibm_operating_system)

        return operating_systems_list

    def get_all_instance_profiles(self, name=None, architecture=None):
        """
        This request lists all instance profiles available in the region. An instance profile specifies the
        performance characteristics and pricing model for an instance.
        :return:
        """
        instance_profiles_list = list()
        response = self.execute(self.format_api_url(LIST_INSTANCE_PROFILES_PATTERN))
        for profile in response.get("profiles", []):
            if profile["vcpu_architecture"]["value"] == "power":
                continue
            ibm_instance_profile = IBMInstanceProfile(
                name=profile["name"], family=profile["family"], cloud_id=self.cloud.id,
                architecture=profile["vcpu_architecture"]["value"])

            if not ((name and name != ibm_instance_profile.name) or
                    (architecture and architecture != ibm_instance_profile.architecture)):
                instance_profiles_list.append(ibm_instance_profile)

        return instance_profiles_list

    def get_instance_ssh_keys(self, instance_id):
        """
        This request retrieves configuration variables used to initialize the instance, such as SSH keys
        and the Windows administrator password.
        :return:
        """
        ssh_keys_list = list()
        response = self.execute(
            self.format_api_url(GET_INSTANCE_SSH_KEYS_PATTERN, instance_id=instance_id)
        )
        if response.get("keys"):
            for key in response["keys"]:
                ibm_key = self.get_all_ssh_keys(name=key.get("name"))
                if ibm_key:
                    ssh_keys_list.append(ibm_key[0])
        return ssh_keys_list

    def get_available_ssh_key_name(self):
        """
        This method returns an available name for SSH key
        :return:
        """
        ssh_keys = self.get_all_ssh_keys()
        used_names = [key.name for key in ssh_keys]

        prefix = "vpc-ssh-key-"
        num = 1
        while True:
            name = "".join([prefix, str(num)])
            if name not in used_names:
                return name
            num += 1

    def get_available_floating_ip_name(self):
        """
        This method returns an available name for Floating IP
        :return:
        """
        floating_ips = self.get_all_floating_ips()
        used_names = [floating_ip.name for floating_ip in floating_ips]

        prefix = "vpc-floating-ip-"
        num = 1
        while True:
            name = "".join([prefix, str(num)])
            if name not in used_names:
                return name
            num += 1

    def get_available_public_gateway_name(self):
        """
        This method returns an available name for Public Gateway
        :return:
        """
        public_gateways = self.get_all_public_gateways()
        used_names = [public_gateway.name for public_gateway in public_gateways]

        prefix = "vpc-pubgw-"
        num = 1
        while True:
            name = "".join([prefix, str(num)])
            if name not in used_names:
                return name
            num += 1

    def get_all_volume_profiles(self, name=None):
        """
        This request lists all volume profiles available in the region. A volume profile specifies
        the performance characteristics and pricing model for a volume.
        :return:
        """
        volume_profiles_list = list()
        response = self.execute(self.format_api_url(LIST_VOLUME_PROFILES_PATTERN))
        if response.get("profiles"):
            for volume in response["profiles"]:
                ibm_volume_profile = IBMVolumeProfile(
                    name=volume["name"],
                    region=self.region,
                    family=volume["family"],
                    generation=volume.get("generation"),
                    cloud_id=self.cloud.id,
                )

                if name and name != ibm_volume_profile.name:
                    continue

                volume_profiles_list.append(ibm_volume_profile)
        return volume_profiles_list

    def get_all_volumes(self, name=None):
        """
        This request lists all volumes in the region. Volumes are network-connected block storage devices
        that may be attached to one or more instances in the same region.
        :return:
        """
        volumes_list = list()
        response = self.execute(self.format_api_url(LIST_VOLUMES_PATTERN))
        if response.get("volumes"):
            for volume in response["volumes"]:
                ibm_volume = IBMVolume(
                    name=volume["name"],
                    capacity=volume["capacity"],
                    zone=volume["zone"]["name"],
                    region=self.region,
                    iops=volume["capacity"],
                    encryption=volume["encryption"],
                    resource_id=volume["id"],
                    cloud_id=self.cloud.id,
                    status=CREATED,
                )

                if name and name != ibm_volume.name:
                    continue

                if volume.get("profile"):
                    profile = self.get_all_volume_profiles(
                        name=volume["profile"]["name"]
                    )
                    ibm_volume.volume_profile = profile[0]

                volumes_list.append(ibm_volume)
            return volumes_list

    def get_all_instances(
        self,
        name=None,
        zone=None,
        vpc_name=None,
        private_ip=None,
        required_relations=True,
    ):
        """
        This request lists all instances in the region.
        :return:
        """
        instances_list = list()
        response = self.execute(self.format_api_url(LIST_INSTANCES_PATTERN))
        if not response.get("instances"):
            return instances_list

        for instance in response["instances"]:
            ibm_instance = IBMInstance(
                name=instance["name"],
                zone=instance["zone"]["name"],
                resource_id=instance["id"],
                status=CREATED,
                cloud_id=self.cloud.id,
                region=self.region,
                state=INST_START,
                instance_status=instance["status"],
            )

            if (name and name != ibm_instance.name) or (
                vpc_name and vpc_name != instance["vpc"]["name"]
            ):
                continue

            if required_relations:
                if instance.get("image"):
                    ibm_image = self.get_all_images(name=instance["image"]["name"])
                    if ibm_image:
                        ibm_instance.ibm_image = ibm_image[0]

                if instance.get("profile"):
                    ibm_profile = self.get_all_instance_profiles(
                        instance["profile"]["name"]
                    )
                    if ibm_profile:
                        ibm_instance.ibm_instance_profile = ibm_profile[0]

                ibm_boot_attachment = None
                if instance.get("boot_volume_attachment"):
                    ibm_boot_attachment = IBMVolumeAttachment(
                        instance["boot_volume_attachment"]["name"],
                        "boot",
                        is_delete=True,
                        resource_id=instance["boot_volume_attachment"]["id"],
                    )
                    ibm_volume = self.get_all_volumes(
                        name=instance["boot_volume_attachment"]["volume"]["name"]
                    )
                    if ibm_volume:
                        ibm_boot_attachment.volume = ibm_volume[0]
                    ibm_instance.volume_attachments.append(ibm_boot_attachment)

                if instance.get("volume_attachments"):
                    for volume_attachment in instance["volume_attachments"]:
                        if ibm_boot_attachment.name == volume_attachment["name"]:
                            continue

                        ibm_attachment = IBMVolumeAttachment(
                            volume_attachment["name"],
                            "data",
                            is_delete=True,
                            resource_id=volume_attachment["id"],
                        )
                        ibm_volume = self.get_all_volumes(
                            name=volume_attachment["volume"]["name"]
                        )
                        if ibm_volume:
                            ibm_attachment.volume = ibm_volume[0]
                        ibm_instance.volume_attachments.append(ibm_attachment)

                ibm_primary_network_interface_name = None
                if instance.get("primary_network_interface"):
                    ibm_primary_network_interface_name = instance[
                        "primary_network_interface"
                    ]["name"]

                found = False
                if instance.get("network_interfaces"):
                    for interface in instance["network_interfaces"]:
                        ibm_network_interface = IBMNetworkInterface(
                            interface["name"],
                            resource_id=interface["id"],
                            private_ip=interface["primary_ipv4_address"],
                        )
                        if ibm_primary_network_interface_name == interface["name"]:
                            ibm_network_interface.is_primary = True

                        if interface.get("subnet"):
                            subnet = self.get_all_subnets(
                                interface["subnet"]["name"],
                                vpc=instance["vpc"]["name"],
                            )
                            ibm_network_interface.ibm_subnet = subnet[0]

                        if not interface.get("security_group"):
                            security_group = self.get_vpc_default_security_group(
                                instance["vpc"]["id"]
                            )
                            if security_group:
                                ibm_network_interface.security_groups.append(
                                    security_group
                                )

                        floating_ip = self.get_network_interface_floating_ip(
                            ibm_instance.resource_id,
                            ibm_network_interface.resource_id,
                        )
                        if floating_ip:
                            ibm_network_interface.floating_ip = floating_ip

                        if ibm_network_interface.private_ip == private_ip:
                            found = True

                        ibm_instance.network_interfaces.append(
                            ibm_network_interface
                        )

                if private_ip and not found:
                    continue

                ssh_keys = self.get_instance_ssh_keys(ibm_instance.resource_id)
                if ssh_keys:
                    ibm_instance.ssh_keys = ssh_keys

                resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                    resource_id=instance["resource_group"]["id"]
                )
                if resource_group:
                    ibm_instance.ibm_resource_group = resource_group[0]

            if not (
                (vpc_name and vpc_name != instance["vpc"]["name"])
                or (zone and zone != ibm_instance.zone)
            ):
                instances_list.append(ibm_instance)

        return instances_list

    
    def get_all_k8s_clusters(self, name=None, vpc=None):
        """
        This request lists all K8S cluster available in a given region
        :return:
        """
        k8s_cluster_list = list()
        time.sleep(60)
        k8s_clusters = self.execute_(self.format_api_url(LIST_K8S_CLUSTERS_PATTERN))
        if not k8s_clusters:
            return k8s_cluster_list

        for k8s_cluster in k8s_clusters:
            ibm_k8s_cluster = KubernetesCluster(
                name=k8s_cluster['name'],
                disable_public_service_endpoint=False,
                kube_version=k8s_cluster['masterKubeVersion'],
                pod_subnet=k8s_cluster['podSubnet'],
                provider=k8s_cluster['provider'],
                cluster_type=k8s_cluster['type'],
                service_subnet=k8s_cluster['serviceSubnet'],
                status=k8s_cluster['status'],
                state=k8s_cluster['state'],
                cloud_id=self.cloud.id
            
            )
            ibm_k8s_cluster.resource_id = k8s_cluster['id']

            resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                resource_id=k8s_cluster["resourceGroup"]
            )
            if resource_group:
                ibm_k8s_cluster.ibm_resource_group = resource_group[0]

            if name == ibm_k8s_cluster.name:
                if k8s_cluster["region"] == self.region:
                    # TODO send parameter "resourcegroup and region"
                    k8s_cluster_worker_pools = self.get_k8s_cluster_worker_pools(k8s_cluster["region"],
                                                                                 k8s_cluster["resourceGroupName"],
                                                                                 k8s_cluster["id"])
                    for k8s_cluster_worker_pool in k8s_cluster_worker_pools:
                        ibm_k8s_cluster_worker_pool = KubernetesClusterWorkerPool(
                            name=k8s_cluster_worker_pool['poolName'],
                            flavor=k8s_cluster_worker_pool["flavor"],
                            worker_count=k8s_cluster_worker_pool["workerCount"],
                            disk_encryption=True
                        )
                        ibm_k8s_cluster_worker_pool.resource_id = k8s_cluster_worker_pool["id"]
                        for k8s_cluster_worker_pool_zone in k8s_cluster_worker_pool['zones']:
                            ibm_k8s_cluster_worker_pool_zone = KubernetesClusterWorkerPoolZone.from_ibm_json_body_zone(
                                k8s_cluster_worker_pool_zone)
                            ibm_subnets = self.get_all_subnets()
                            if ibm_subnets:
                                for zone_subnet in k8s_cluster_worker_pool_zone['subnets']:
                                    for subnet in ibm_subnets:
                                        if subnet.resource_id == zone_subnet['id']:
                                            ibm_k8s_cluster_worker_pool_zone.subnet_id = zone_subnet['id']
                                ibm_k8s_cluster_worker_pool.zones.append(ibm_k8s_cluster_worker_pool_zone)
                            ibm_k8s_cluster.worker_pools.append(ibm_k8s_cluster_worker_pool)
                    k8s_cluster_list.append(ibm_k8s_cluster)
        return k8s_cluster_list
    
    def get_k8s_cluster_worker_pools(self, region=None, resource_group=None, k8s_cluster_id=None):
    
        k8s_cluster_worker_pools = self.execute_(self.format_api_url(GET_K8S_CLUSTERS_WORKER_POOL,
                                                                     cluster=k8s_cluster_id),
                                                 resource_group=resource_group,
                                                 region=region)
        return k8s_cluster_worker_pools

    def get_all_k8s_cluster_worker_pool(self, cluster_id, workerpool_name=None, region=None):
        """
        This request lists all the K8s Workerpools exist in K8s Cluster for region.
        :return:
        """
        worker_pool_list = list()

        k8s_cluster_worker_pools = self.get_k8s_cluster_worker_pools(
                region=region,
                k8s_cluster_id=cluster_id
        )

        if not k8s_cluster_worker_pools:
            return worker_pool_list

        for k8s_cluster_worker_pool in k8s_cluster_worker_pools:
            ibm_k8s_cluster_worker_pool = KubernetesClusterWorkerPool(
                name=k8s_cluster_worker_pool['poolName'],
                flavor=k8s_cluster_worker_pool["flavor"],
                worker_count=k8s_cluster_worker_pool["workerCount"],
                disk_encryption=True
            )
            ibm_k8s_cluster_worker_pool.resource_id = k8s_cluster_worker_pool["id"]
            for k8s_cluster_worker_pool_zone in k8s_cluster_worker_pool['zones']:
                ibm_k8s_cluster_worker_pool_zone = KubernetesClusterWorkerPoolZone.from_ibm_json_body_zone(
                    k8s_cluster_worker_pool_zone)
                ibm_subnets = self.get_all_subnets()
                if ibm_subnets:
                    for zone_subnet in k8s_cluster_worker_pool_zone['subnets']:
                        for subnet in ibm_subnets:
                            if subnet.resource_id == zone_subnet['id']:
                                ibm_k8s_cluster_worker_pool_zone.subnet_id = zone_subnet['id']
                    ibm_k8s_cluster_worker_pool.zones.append(ibm_k8s_cluster_worker_pool_zone)

            if workerpool_name:
                if workerpool_name == k8s_cluster_worker_pool["poolName"]:
                    worker_pool_list.append(ibm_k8s_cluster_worker_pool)
            else:
                worker_pool_list.append(ibm_k8s_cluster_worker_pool)

        return worker_pool_list


    def get_all_load_balancers(self, name=None, vpc_name=None, required_relations=True):
        """
        This request lists all load balancers available in a given region
        :return:
        """
        load_balancer_list = list()
        response = self.execute(self.format_api_url(LIST_LOAD_BALANCERS_PATTERN))
        if not response.get("load_balancers"):
            return load_balancer_list

        for load_balancer in response["load_balancers"]:
            ibm_load_balancer = IBMLoadBalancer(
                name=load_balancer["name"], is_public=load_balancer["is_public"], region=self.region,
                provisioning_status=load_balancer["provisioning_status"], host_name=load_balancer["hostname"],
                status=CREATED, resource_id=load_balancer["id"], cloud_id=self.cloud.id)

            if name and name != ibm_load_balancer.name:
                continue

            if load_balancer.get("subnets"):
                for subnet in load_balancer["subnets"]:
                    ibm_subnets = self.get_all_subnets(name=subnet["name"], vpc=vpc_name)
                    if ibm_subnets:
                        ibm_load_balancer.subnets.append(ibm_subnets[0])

            if vpc_name and not ibm_load_balancer.subnets.all():
                continue

            if load_balancer.get("public_ips"):
                public_ips_list = list()
                for ip in load_balancer["public_ips"]:
                    public_ips_list.append(ip["address"])

                ibm_load_balancer.public_ips = {"public_ips": public_ips_list}

            if load_balancer.get("private_ips"):
                private_ips_list = list()
                for ip in load_balancer["private_ips"]:
                    private_ips_list.append(ip["address"])

                ibm_load_balancer.private_ips = {"private_ips": private_ips_list}

            if required_relations:
                if load_balancer.get("listeners"):
                    ibm_listeners = self.get_all_listeners(load_balancer_id=ibm_load_balancer.resource_id)
                    if ibm_listeners:
                        ibm_load_balancer.listeners = ibm_listeners

                if load_balancer.get("pools"):
                    ibm_pools = self.get_all_pools(load_balancer_id=ibm_load_balancer.resource_id)
                    if ibm_pools:
                        ibm_load_balancer.pools = ibm_pools

                resource_group = self.resource_ops.fetch_ops.get_resource_groups(
                    resource_id=load_balancer["resource_group"]["id"])
                if resource_group:
                    ibm_load_balancer.ibm_resource_group = resource_group[0]

            load_balancer_list.append(ibm_load_balancer)
        return load_balancer_list

    def get_all_listeners(self, load_balancer_id):
        """
        This request lists all listeners of a load balancer
        :return:
        """
        listeners_list = list()
        response = self.execute(
            self.format_api_url(LIST_LOAD_BALANCERS_LISTENERS_PATTERN, load_balancer_id=load_balancer_id))
        if response.get("listeners"):
            for listener in response["listeners"]:
                ibm_listener = IBMListener(
                    listener["port"],
                    listener["protocol"],
                    listener.get("limit"),
                    listener.get("crn"),
                    listener["id"],
                    CREATED,
                )

                if listener.get("default_pool"):
                    default_pool = self.get_all_pools(
                        load_balancer_id=load_balancer_id,
                        name=listener["default_pool"]["name"],
                    )
                    if default_pool:
                        ibm_listener.ibm_pool = default_pool[0]

                listeners_list.append(ibm_listener)
        return listeners_list

    def get_all_pools(self, load_balancer_id, name=None):
        """
        This request lists all pools of a load balancer
        :return:
        """
        pools_list = list()
        response = self.execute(
            self.format_api_url(LIST_LOAD_BALANCERS_POOLS_PATTERN, load_balancer_id=load_balancer_id))
        if response.get("pools"):
            for pool in response["pools"]:
                ibm_pool = IBMPool(
                    pool["name"],
                    pool["algorithm"],
                    pool["protocol"],
                    resource_id=pool["id"],
                    status=CREATED,
                )

                if name and name != ibm_pool.name:
                    continue

                if pool.get("session_persistence"):
                    ibm_pool.session_persistence = pool["session_persistence"]["type"]

                if pool.get("health_monitor"):
                    ibm_health_check = IBMHealthCheck(
                        pool["health_monitor"].get("delay"),
                        pool["health_monitor"].get("max_retries"),
                        pool["health_monitor"].get("timeout"),
                        pool["health_monitor"].get("type"),
                        pool["health_monitor"].get("url_path"),
                        pool["health_monitor"].get("port"),
                    )
                    ibm_pool.health_check = ibm_health_check

                if pool.get("members"):
                    members = self.get_all_members(load_balancer_id, ibm_pool.resource_id)
                    if members:
                        ibm_pool.pool_members = members

                pools_list.append(ibm_pool)
        return pools_list

    def get_all_members(self, load_balancer_id, pool_id):
        """
        This request retrieves a list of all members that belong to the pool.
        :return:
        """
        members_list = list()
        response = self.execute(
            self.format_api_url(
                LIST_POOL_MEMBERS_PATTERN,
                load_balancer_id=load_balancer_id,
                pool_id=pool_id,
            )
        )
        if response.get("members"):
            for member in response["members"]:
                ibm_member = IBMPoolMember(member["port"], member["weight"], member["id"], status=CREATED)
                if member.get("target"):
                    instance = self.get_all_instances(
                        private_ip=member["target"]["address"]
                    )
                    if instance:
                        ibm_member.instance = instance[0]

                members_list.append(ibm_member)
        return members_list

    def get_load_balancer_status(self, load_balancer_id):
        """
        This request retrieves a single load balancer specified by the identifier in the URL path.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_LOAD_BALANCER_PATTERN, load_balancer_id=load_balancer_id
            )
        )
        return response.get("provisioning_status")

    def get_all_ibm_vpc_routes(self, vpc_resource_id, name, zone=None):
        """
        This request retrieves all user-defined routes for a VPC
        :return:
        """
        routes_list = list()
        response = self.execute(
            self.format_api_url(LIST_VPC_ROUTES, vpc_id=vpc_resource_id, zone_name=zone)
        )
        if response.get("routes"):
            for route in response["routes"]:
                if name and name != route["name"]:
                    continue

                ibm_vpc_route = IBMVpcRoute(
                    name=route["name"],
                    resource_id=route["id"],
                    region=self.region,
                    zone=route["zone"]["name"],
                    created_at=datetime.strptime(route["created_at"], '%Y-%m-%dT%H:%M:%SZ'),
                    destination=route["destination"],
                    lifecycle_state=route["lifecycle_state"],
                    next_hop_address=route["next_hop"]["address"],
                    cloud_id=self.cloud.id,
                )

                routes_list.append(ibm_vpc_route)
        return routes_list

    def get_image_status(self, image_id):
        """
        This request retrieves a single Image specified by the identifier in the URL path.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_IMAGE_PATTERN, image_id=image_id)
        )
        return response.get("status")

    def get_floating_ip_status(self, floating_ip_id):
        """
        This request retrieves a single Floating IP specified by the identifier in the URL path.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_FLOATING_IP_PATTERN, floating_ip_id=floating_ip_id)
        )
        return response.get("status")

    def get_image(self, image_id):
        """
        This request retrieves a single Image specified by the identifier in the URL path.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_IMAGE_PATTERN, image_id=image_id)
        )
        if response.get("id"):
            ibm_image = IBMImage(
                name=response.get("name"),
                visibility=response.get("visibility"),
                resource_id=response.get("id"),
                cloud_id=self.cloud.id,
                status=CREATED,
                region=self.region,
                size=response["file"].get("size"),
            )
            return ibm_image

    def get_floating_ip(self, floating_ip_id):
        """
        This request retrieves a single Floating IP specified by the identifier in the URL path.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_FLOATING_IP_PATTERN, floating_ip_id=floating_ip_id)
        )
        if response.get("id"):
            ibm_floating_ip = IBMFloatingIP(
                response.get("name"),
                self.region,
                response["zone"].get("name"),
                response.get("address"),
                response.get("id"),
                CREATED,
                self.cloud.id,
            )
            return ibm_floating_ip

    def get_vpc_route(self, vpc_route_id):
        """
        This request retrieves a single route specified by the identifier in the URL.
        """
        vpc_route = IBMVpcRoute.query.filter_by(cloud_id=self.cloud.id).first()
        response = self.execute(
            self.format_api_url(
                GET_VPC_ROUTE_PATTERN,
                vpc_id=vpc_route.ibm_vpc_network.resource_id,
                route_id=vpc_route_id,
            )
        )
        if response.get("id"):
            ibm_vpc_route = IBMVpcRoute(
                name=response.get("name"),
                resource_id=response.get("id"),
                region=self.region,
                zone=response["zone"].get("name"),
                created_at=response.get("created_at"),
                lifecycle_state=response.get("lifecycle_state"),
                next_hop_address=response["next_hop"].get("address"),
                cloud_id=self.cloud.id,
            )
            return ibm_vpc_route

    def get_vpc(self, vpc_id):
        """
        This request retrieves a single VPC specified by the identifier in the URL.
        :return:
        """
        response = self.execute(self.format_api_url(GET_VPC_PATTERN, vpc_id=vpc_id))
        if response.get("id"):
            ibm_vpc = IBMVpcNetwork(
                name=response.get("name"),
                region=self.region,
                classic_access=response.get("classic_access"),
                cloud_id=self.cloud.id,
                resource_id=response.get("id"),
                status=CREATED,
            )
            return ibm_vpc

    def get_subnet(self, subnet_id):
        """
        This request retrieves a single subnet specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_SUBNET_PATTERN, subnet_id=subnet_id)
        )
        if response.get("id"):
            ibm_subnet = IBMSubnet(
                name=response.get("name"),
                zone=response["zone"].get("name"),
                ipv4_cidr_block=response.get("ipv4_cidr_block"),
                resource_id=response.get("id"),
                status=CREATED,
                cloud_id=self.cloud.id,
                region=self.region,
            )
            return ibm_subnet

    def get_ike_policy(self, ike_policy_id):
        """
        This request retrieves a single  policyike specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_IKE_POLICY_PATTERN, ike_policy_id=ike_policy_id)
        )
        if response.get("id"):
            ibm_ike_policy = IBMIKEPolicy(
                response.get("name"),
                self.region,
                response.get("key_lifetime"),
                CREATED,
                response.get("ike_version"),
                response.get("authentication_algorithm"),
                response.get("encryption_algorithm"),
                response.get("dh_group"),
                response.get("id"),
                self.cloud.id,
            )
            return ibm_ike_policy

    def get_ipsec_policy(self, ipsec_policy_id):
        """
        This request retrieves a single ipsec policy specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_IPSEC_POLICY_PATTERN, ipsec_policy_id=ipsec_policy_id
            )
        )
        if response.get("id"):
            ibm_ipsec_policy = IBMIPSecPolicy(
                response.get("name"),
                self.region,
                response.get("key_lifetime"),
                CREATED,
                response.get("authentication_algorithm"),
                response.get("encryption_algorithm"),
                response.get("pfs"),
                response.get("id"),
                self.cloud.id,
            )

            return ibm_ipsec_policy

    def get_vpn_connection(self, connection_id, vpn_gateway_id):
        """
        This request retrieves a single vpn connection specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_VPN_CONNECTION_PATTERN,
                vpn_gateway_id=vpn_gateway_id,
                connection_id=connection_id,
            )
        )
        if response.get("id"):
            ibm_vpn_connection = IBMVpnConnection(
                response.get("name"),
                response.get("peer_address"),
                response.get("psk"),
                json.dumps(response.get("local_cidrs"))
                if response.get("local_cidrs")
                else [],
                json.dumps(response.get("peer_cidrs"))
                if response.get("peer_cidrs")
                else [],
                response["dead_peer_detection"].get("interval"),
                response["dead_peer_detection"].get("timeout"),
                dpd_action=response["dead_peer_detection"].get("action"),
                resource_id=response.get("id"),
                authentication_mode=response.get("authentication_mode"),
                created_at=response.get("created_at"),
                vpn_status=response.get("status"),
                route_mode=response.get("route_mode"),
            )
            return ibm_vpn_connection

    def get_vpn_gateway(self, vpn_gateway_id):
        """
        This request retrieves a single vpn connection specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_VPN_GATEWAY_PATTERN, vpn_gateway_id=vpn_gateway_id)
        )
        if response.get("id"):
            ibm_vpn_gateway = IBMVpnGateway(
                name=response.get("name"),
                region=self.region,
                status=CREATED,
                resource_id=response.get("id"),
                public_ip=response["public_ip"].get("address"),
                created_at=response.get("created_at"),
                gateway_status=response.get("status"),
                cloud_id=self.cloud.id,
            )
            return ibm_vpn_gateway

    def get_network_acl(self, acl):
        response = self.execute(
            self.format_api_url(GET_ACL_PATTERN, acl_id=acl.resource_id)
        )
        if response.get("id"):
            ibm_network_acl = IBMNetworkAcl(
                response.get("name"),
                self.region,
                response.get("id"),
                status=CREATED,
                cloud_id=self.cloud.id,
            )
            return ibm_network_acl

    def get_network_acl_rule(self, acl_rule):
        response = self.execute(
            self.format_api_url(
                GET_ACL_RULE_PATTERN,
                acl_id=acl_rule.ibm_network_acl.resource_id,
                rule_id=acl_rule.resource_id,
            )
        )
        if response.get("id"):
            ibm_network_acl_rule = IBMNetworkAclRule(
                response.get("name"),
                response.get("action"),
                response.get("destination"),
                response.get("direction"),
                response.get("source"),
                response.get("protocol"),
                response.get("port_max"),
                response.get("port_min"),
                response.get("source_port_max"),
                response.get("source_port_min"),
                response.get("code"),
                response.get("type"),
                status=CREATED,
            )
            return ibm_network_acl_rule

    def get_volume(self, volume):
        response = self.execute(
            self.format_api_url(GET_VOLUME_PATTERN, volume_id=volume.resource_id)
        )
        if response.get("id"):
            ibm_volume = IBMVolume(
                name=response.get("name"),
                capacity=response.get("capacity"),
                zone=response["zone"].get("name"),
                region=self.region,
                iops=response.get("capacity"),
                encryption=response.get("encryption"),
                resource_id=response.get("id"),
                cloud_id=self.cloud.id,
                status=CREATED
            )
            return ibm_volume

    def get_address_prefix(self, address_prefix):
        """
        This request retrieve single address pool prefixe for a VPC.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_ADDRESS_PREFIXES_PATTERN,
                vpc_id=address_prefix.ibm_vpc_network.resource_id,
                address_prefix_id=address_prefix.resource_id,
            )
        )
        if response.get("id"):
            ibm_address_prefix = IBMAddressPrefix(
                name=response.get("name"),
                zone=response["zone"].get("name"),
                address=response.get("cidr"),
                resource_id=response.get("id"),
                status=CREATED,
                is_default=response.get("is_default"),
            )
            return ibm_address_prefix

    def get_public_gateway(self, public_gateway_id):
        """
        This request retrieves a single Public Gateway specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_PUBLIC_GATEWAY_PATTERN, public_gateway_id=public_gateway_id
            )
        )
        if response.get("id"):
            ibm_public_gateway = IBMPublicGateway(
                name=response.get("name"),
                zone=response["zone"].get("name"),
                resource_id=response.get("id"),
                status=CREATED,
                region=self.region,
                cloud_id=self.cloud.id,
            )
            return ibm_public_gateway

    def get_security_group(self, security_group_obj):
        """
        This request retrieves a Security Group.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_SECURITY_GROUP_PATTERN,
                security_group_id=security_group_obj.resource_id,
            )
        )
        if response.get("id"):
            ibm_security_group = IBMSecurityGroup(
                name=response.get("name"),
                resource_id=response.get("id"),
                status=CREATED,
                cloud_id=self.cloud.id,
                region=self.region,
            )
            return ibm_security_group

    def get_security_group_rule(self, security_group_rule_obj):
        """
        This request retrieves a IBM security group rule.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_SECURITY_GROUP_RULE_PATTERN,
                security_group_id=security_group_rule_obj.security_group.resource_id,
                rule_id=security_group_rule_obj.resource_id,
            )
        )
        if response.get("id"):
            ibm_rule = IBMSecurityGroupRule(
                response.get("direction"),
                response.get("protocol"),
                response.get("code"),
                response.get("type"),
                response.get("port_min"),
                response.get("port_max"),
                response.get("address"),
                response.get("cidr_block"),
                resource_id=response.get("id"),
                status=CREATED,
            )
            return ibm_rule

    def get_instance(self, instance_id):
        """
        This request retrieves a single instance specified by the identifier in the URL.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_INSTANCE_PATTERN, instance_id=instance_id)
        )
        if response.get("id"):
            ibm_instance = IBMInstance(
                name=response.get("name"),
                zone=response["zone"].get("name"),
                resource_id=response.get("id"),
                status=CREATED,
                cloud_id=self.cloud.id,
                region=self.region,
                state=INST_START,
                instance_status=response.get("status"),
            )
            return ibm_instance

    def get_load_balancer_listener(self, load_balancer, listener):
        """
        This request retrieves a single listener
       """
        response = self.execute(
            self.format_api_url(
                GET_LOAD_BALANCER_LISTENER_PATTERN,
                listener_id=listener.resource_id,
                load_balancer_id=load_balancer.resource_id,
            )
        )
        if response.get("id"):
            ibm_listener = IBMListener(
                response.get("port"),
                response.get("protocol"),
                response.get("limit"),
                response.get("crn"),
                response.get("id"),
                CREATED,
            )
            return ibm_listener

    def get_ssh_key(self, ssh_key):
        """
        this request retrieves a single ssh key
        """
        response = self.execute(
            self.format_api_url(GET_SSH_KEY_PATTERN, ssh_key_id=ssh_key.resource_id,)
        )
        if response.get("id"):
            ibm_key = IBMSshKey(
                name=response.get("name"),
                type_=response.get("type"),
                public_key=response.get("public_key"),
                region=self.region,
                finger_print=response.get("fingerprint"),
                status=CREATED,
                resource_id=response.get("id"),
                cloud_id=self.cloud.id,
            )
            return ibm_key

    def get_load_balancer(self, load_balancer_id):
        """
        This request retrieves a single load balancer specified by the identifier in the URL path.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                GET_LOAD_BALANCER_PATTERN, load_balancer_id=load_balancer_id
            )
        )
        if response.get("id"):
            ibm_load_balancer = IBMLoadBalancer(
                name=response.get("name"),
                is_public=response.get("is_public"),
                region=self.region,
                provisioning_status=response.get("provisioning_status"),
                host_name=response.get("hostname"),
                status=CREATED,
                resource_id=response.get("id"),
                cloud_id=self.cloud.id,
            )
            return ibm_load_balancer

    def get_local_cidr(self, gateway_resource_id, connection_resource_id, prefix, prefix_length):
        """
        Get specific local CIDR for VPN Connection
        :return:
        """
        response = self.execute(self.format_api_url(
            GET_LOCAL_CIDRS_VPN_CONNECTION, vpn_gateway_id=gateway_resource_id,
            id=connection_resource_id, prefix_address=prefix, prefix_length=prefix_length
            )
        )
        if response.status_code == 204:
            return True
        return False

    def get_peer_cidr(self, gateway_resource_id, connection_resource_id, prefix, prefix_length):
        """
        Get specific Peer CIDR for VPN connection
        :return:
        """
        response = self.execute( self.format_api_url(
            GET_PEER_SUBNET_VPN_CONNECTION, vpn_gateway_id=gateway_resource_id,
                                id=connection_resource_id, prefix_address=prefix, prefix_length=prefix_length
            )
        )
        if response.status_code == 204:
            return True
        return False

    @staticmethod
    def format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the unformatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def execute(self, request, data=None):
        request_url = request[1].format(base_url=self.base_url, version=VERSION, generation=GENERATION)
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)
        try:
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(IBMCredentials(self.iam_ops.authenticate_cloud_account()))

            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.debug("{0} : {1}".format(request[0], request_url))
            response = self.session.request(request[0], request_url, data=data, timeout=50, headers=headers)
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request_url)
        else:
            if response.status_code == 401:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code in [400, 408, 500]:
                raise IBMExecuteError(response)
            elif response.status_code not in [200, 201, 204, 404]:
                raise IBMExecuteError(response)

            resp =response.json()
            if not (request[0] == "GET" and "next" in resp):
                return resp

            list_key = None
            for key, val in resp.items():
                if isinstance(val, list):
                    list_key = key

            if not list_key:
                return resp

            temp_resp = resp.copy()
            while "next" in temp_resp:
                req = [
                    "GET",
                    temp_resp["next"]["href"] + "&version={version}&generation={generation}".format(
                        version=VERSION, generation=GENERATION)
                ]
                temp_resp = self.execute(req)
                resp[list_key].extend(temp_resp[list_key][:])

            return resp
    
    def execute_(self, request, data=None, resource_group=None, region=None):
        request_url = request[1].format(k8s_base_url=self.k8s_base_url)
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)
        try:
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(IBMCredentials(self.iam_ops.authenticate_cloud_account()))

            headers = {"Authorization": self.cloud.credentials.access_token}
            if resource_group:
                headers.update({"Auth-Resource-Group": resource_group})
            if region:
                headers.update({"X-Region": region})
            current_app.logger.debug("{0} : {1}".format(request[0], request_url))
            response = self.session_k8s.request(request[0], request_url, data=data, timeout=50, headers=headers)
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request_url)
        else:
            if response.status_code == 401:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code in [400, 408, 500]:
                raise IBMExecuteError(response)
            elif response.status_code not in [200, 201, 204, 404]:
                raise IBMExecuteError(response)

            resp =response.json()
            if not (request[0] == "GET" and "next" in resp):
                return resp

            list_key = None
            for key, val in resp.items():
                if isinstance(val, list):
                    list_key = key

            if not list_key:
                return resp

            temp_resp = resp.copy()
            while "next" in temp_resp:
                req = [
                    "GET",
                    temp_resp["next"]["href"] + "&version={version}&generation={generation}".format(
                        version=VERSION, generation=GENERATION)
                ]
                temp_resp = self.execute(req)
                resp[list_key].extend(temp_resp[list_key][:])

            return resp
