import json

from doosra.common.consts import CREATION_PENDING
from doosra.common.utils import is_private, is_private_ip, get_network, transform_ibm_name, remove_duplicates
from doosra.migration.consts import VENDOR_DICTIONARY
from doosra.models import (
    IBMIKEPolicy,
    IBMIPSecPolicy,
    IBMNetworkAcl,
    IBMSubnet,
    IBMVpnConnection,
    IBMVpnGateway,
    IBMNetworkAclRule,
    IBMListener,
    IBMLoadBalancer,
    IBMHealthCheck,
    IBMPool,
    IBMSshKey,
    IBMImage,
    IBMInstance,
    IBMInstanceProfile,
    IBMNetworkInterface,
    IBMPoolMember,
    IBMSecurityGroup,
    IBMSecurityGroupRule,
    IBMOperatingSystem,
    IBMVolumeAttachment,
    IBMVolume,
    IBMVolumeProfile,
)


class SoftLayerInstance(object):
    NAME_KEY = "name"
    IMAGE_KEY = "image"
    SSH_KEYS = "ssh_keys"
    INSTANCE_PROFILE_KEY = "instance_profile"
    NETWORK_INTERFACE_KEY = "network_interfaces"
    VOLUME_KEY = "volume"
    DATA_CENTER_KEY = "data_center"
    INSTANCE_TYPE_KEY = "instance_type"
    AUTO_SCALE_GROUP_KEY = "auto_scale_group"
    NETWORK_ATTACH_STORAGES_KEY = "network_attached_storages"
    DEDICATED_HOST_ID_KEY = "dedicated_host_id"

    def __init__(self, name, image=None, ssh_keys=None, instance_profile=None, network_interfaces=None,
                 volumes=None, instance_id=None, data_center=None, instance_type=None, dedicated_host_id=None,
                 auto_scale_group=None,
                 network_attached_storages=None):
        self.name = name
        self.image = image
        self.ssh_keys = ssh_keys or list()
        self.instance_profile = instance_profile
        self.network_interfaces = network_interfaces or list()
        self.volumes = volumes or list()
        self.instance_id = instance_id or None
        self.data_center = data_center
        self.auto_scale_group = auto_scale_group
        self.network_attached_storages = network_attached_storages
        self.instance_type = instance_type
        self.dedicated_host_id = dedicated_host_id

    @classmethod
    def from_softlayer_json(cls, instance_json):
        return cls(
            name=instance_json["hostname"].lower(),
            instance_id=instance_json.get("id"),
            data_center=instance_json["datacenter"].get("longName"),
            instance_type=instance_json["type"].get("keyName"),
            dedicated_host_id=instance_json["dedicatedHost"]["id"] if instance_json.get('dedicatedHost') else None
        )

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.IMAGE_KEY: self.image.to_json() if self.image else None,
            self.INSTANCE_PROFILE_KEY: self.instance_profile.to_json() if self.instance_profile else None,
            self.SSH_KEYS: [ssh_key.to_json() for ssh_key in self.ssh_keys] if self.ssh_keys else None,
            self.NETWORK_INTERFACE_KEY: [network.to_json() for network in self.network_interfaces],
            self.VOLUME_KEY: [v.to_json() for v in self.volumes],
            self.DATA_CENTER_KEY: self.data_center,
            self.INSTANCE_TYPE_KEY: self.instance_type,
            self.AUTO_SCALE_GROUP_KEY: self.auto_scale_group,
            self.NETWORK_ATTACH_STORAGES_KEY: self.network_attached_storages,
            self.DEDICATED_HOST_ID_KEY: self.dedicated_host_id
        }

    def to_ibm(self):
        ibm_instance = IBMInstance(
            name=self.name, zone="dummy-zone", region="dummy-region", status=CREATION_PENDING,
            classical_instance_id=self.instance_id, data_center=self.data_center, instance_type=self.instance_type,
            auto_scale_group=self.auto_scale_group, network_attached_storages=self.network_attached_storages)
        ibm_instance.ibm_image = self.image.to_ibm() if self.image else None
        ibm_instance.ibm_instance_profile = self.instance_profile.to_ibm() if self.instance_profile else None
        ibm_instance.ssh_keys = [ssh_key.to_ibm() for ssh_key in self.ssh_keys] if self.ssh_keys else []
        ibm_instance.volume_attachments = [v.to_ibm() for v in self.volumes] if self.volumes else []
        ibm_boot_volume_attachment = IBMVolumeAttachment(
            "{}-boot-volume-attachment".format(self.name), type_="boot", is_delete=True)
        ibm_instance.volume_attachments.append(ibm_boot_volume_attachment)

        for network_interface in self.network_interfaces:
            if network_interface.is_public_interface:
                continue

            ibm_instance.network_interfaces.append(network_interface.to_ibm())

        return ibm_instance


class SoftLayerImage(object):
    NAME_KEY = "name"
    OS_NAME_KEY = "os_name"
    OS_VERSION_KEY = "os_version"
    OS_VENDOR_KEY = "os_vendor"
    VISIBILITY_KEY = "visibility"

    def __init__(self, name, os_name=None, os_version=None, os_vendor=None, visibility="private"):
        self.name = name
        self.os_name = os_name
        self.os_version = os_version
        self.os_vendor = os_vendor
        self.visibility = visibility

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.OS_NAME_KEY: self.os_name,
            self.OS_VERSION_KEY: self.os_version,
            self.OS_VENDOR_KEY: self.os_vendor,
            self.VISIBILITY_KEY: self.visibility,
        }

    def to_ibm(self):
        ibm_image = IBMImage(self.name, self.visibility)
        ibm_image.operating_system = IBMOperatingSystem(
            self.os_name, "amd64", None, VENDOR_DICTIONARY.get(self.os_vendor), self.os_version)
        return ibm_image

    @classmethod
    def from_softlayer_json(cls, operating_system):
        return cls(name=operating_system.get("longDescription"), os_name=operating_system.get("longDescription"),
                   os_version=operating_system.get("version"),
                   os_vendor=operating_system["manufacturer".lower()])


class SoftLayerInstanceProfile(object):
    NAME_KEY = "name"
    FAMILY_KEY = "family"

    def __init__(self, name, family):
        self.name = name
        self.family = family

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.FAMILY_KEY: self.family
        }

    def to_ibm(self):
        return IBMInstanceProfile(self.name, self.family)


class SoftLayerVolume(object):
    NAME_KEY = "name"
    CAPACITY_KEY = "capacity"
    PROFILE_KEY = "profile"
    IOPS_KEY = "iops"
    DELETE_VOLUME_KEY = "delete_volume"
    IS_BOOT_VOLUME_KEY = "is_boot_volume"

    def __init__(self, name, capacity, profile, iops, delete_volume, is_boot_volume=None):
        self.name = name
        self.capacity = capacity
        self.profile = profile
        self.iops = iops
        self.delete_volume = delete_volume
        self.is_boot_volume = is_boot_volume

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.CAPACITY_KEY: self.capacity,
            self.PROFILE_KEY: self.profile,
            self.IOPS_KEY: self.iops,
            self.DELETE_VOLUME_KEY: self.delete_volume,
            self.IS_BOOT_VOLUME_KEY: self.is_boot_volume,
        }

    def to_ibm(self):
        ibm_volume_attachment = IBMVolumeAttachment(
            name=transform_ibm_name(self.name), type_="boot" if self.is_boot_volume else "data",
            is_delete=self.delete_volume)
        volume_profile = IBMVolumeProfile("10iops-tier", "dummy-region", "tiered")
        ibm_volume = IBMVolume(
            transform_ibm_name(self.name), self.capacity, zone="dummy-zone", iops="10iops-tier",
            encryption="provider_managed", region="dummy-region")

        ibm_volume.volume_profile = volume_profile
        ibm_volume_attachment.volume = ibm_volume
        return ibm_volume_attachment

    @classmethod
    def from_softlayer_json(cls, name, volume_json):
        return cls(name=name, capacity=volume_json["diskImage"].get("capacity"), profile="general-profile",
                   iops=3000, delete_volume=True, is_boot_volume=volume_json.get("bootableFlag"))


class SoftLayerSshKey(object):
    NAME_KEY = "name"
    TYPE_KEY = "type"
    PUBLIC_KEY = "public_key"
    FINGER_PRINT_KEY = "finger_print"

    def __init__(self, name, type_, public_key, finger_print=None):
        self.name = name
        self.finger_print = finger_print
        self.type = type_ or "rsa"
        self.public_key = public_key

    @classmethod
    def from_softlayer_json(cls, ssh_key_json):
        return cls(name=ssh_key_json.get("label"), type_="rsa", public_key=ssh_key_json.get("key"),
                   finger_print=ssh_key_json.get("fingerprint"))

    def to_json(self):
        return {self.NAME_KEY: self.name}

    def to_ibm(self):
        return IBMSshKey(
            transform_ibm_name(self.name),
            self.type,
            self.public_key,
            "dummy-region",
            self.finger_print,
            status=CREATION_PENDING
        )


class SoftLayerNetworkInterface(object):
    ID_KEY = "id"
    NAME_KEY = "name"
    SUBNET_KEY = "subnet"
    SECURITY_GROUP_KEY = "security_groups"
    PRIVATE_IP_KEY = "private_ip"
    FLOATING_IP_KEY = "floating_ip"
    IS_PRIMARY_KEY = "is_primary"
    IS_PUBLIC_INTERFACE_KEY = "is_public_interface"

    def __init__(
            self, name, private_ip=None, subnet=None, security_groups=None, is_primary=None, is_public_interface=None
    ):
        self.name = name
        self.subnet = subnet
        self.private_ip = private_ip
        self.is_primary = is_primary
        self.is_public_interface = is_public_interface
        self.security_groups = security_groups or list()

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.PRIVATE_IP_KEY: self.private_ip,
            self.IS_PUBLIC_INTERFACE_KEY: self.is_public_interface,
            self.SUBNET_KEY: self.subnet.to_json() if self.subnet else None,
            self.IS_PRIMARY_KEY: self.is_primary,
            self.SECURITY_GROUP_KEY: [
                security_group.to_json() for security_group in self.security_groups
            ]
            if self.security_groups
            else [],
        }

    def to_ibm(self):
        ibm_network_interface = IBMNetworkInterface(
            transform_ibm_name(self.name),
            self.is_primary,
            private_ip=self.private_ip
        )
        if self.subnet:
            ibm_network_interface.ibm_subnet = self.subnet.to_ibm()

        if self.security_groups:
            ibm_network_interface.security_groups.extend(
                [security_group.to_ibm() for security_group in self.security_groups]
                if self.security_groups
                else []
            )

        return ibm_network_interface


class SoftLayerLoadBalancer(object):
    NAME_KEY = "name"
    IS_PUBLIC_KEY = "is_public"
    HOST_NAME_KEY = "host_name"
    LISTENERS_KEY = "listeners"
    POOLS_KEY = "pools"
    SUBNETS_KEY = "subnets"

    def __init__(
            self, name, is_public, host_name, listeners=None, pools=None, subnets=None
    ):
        self.name = name
        self.is_public = True if is_public == 1 else False
        self.host_name = host_name
        self.listeners = listeners or list()
        self.pools = pools or list()
        self.subnets = subnets or list()

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.IS_PUBLIC_KEY: self.is_public,
            self.HOST_NAME_KEY: self.host_name,
            self.LISTENERS_KEY: [listener.to_json() for listener in self.listeners],
            self.POOLS_KEY: [pool.to_json() for pool in self.pools],
            self.SUBNETS_KEY: [subnet.to_json() for subnet in self.subnets],
        }

    def to_ibm(self):
        ibm_load_balancer = IBMLoadBalancer(
            transform_ibm_name(self.name), self.is_public, "dummy-region", status=CREATION_PENDING
        )
        ibm_load_balancer.host_name = self.host_name

        for listener in self.listeners:
            ibm_listener = listener.to_ibm()
            ibm_load_balancer.pools.append(ibm_listener.ibm_pool)
            ibm_load_balancer.listeners.append(ibm_listener)

        for subnet in self.subnets:
            ibm_load_balancer.subnets.append(subnet.to_ibm())

        return ibm_load_balancer


class SoftLayerListener(object):
    PROTOCOL_KEY = "protocol"
    PORT_KEY = "port"
    CONNECTION_LIMIT = "connection_limit"
    BACKEND_POOL_KEY = "backend_pool"

    def __init__(self, protocol, port, connection_limit, backend_pool=None):
        self.protocol = protocol
        self.port = port
        self.connection_limit = connection_limit
        self.backend_pool = backend_pool

    def to_json(self):
        return {
            self.PROTOCOL_KEY: self.protocol,
            self.PORT_KEY: self.port,
            self.CONNECTION_LIMIT: self.connection_limit,
            self.BACKEND_POOL_KEY: self.backend_pool.to_json()
            if self.backend_pool
            else None,
        }

    def to_ibm(self):
        ibm_listener = IBMListener(
            self.port, self.protocol.lower(), self.connection_limit
        )
        if self.backend_pool:
            ibm_listener.ibm_pool = self.backend_pool.to_ibm()

        return ibm_listener


class SoftLayerBackendPool(object):
    ALGORITHM_KEY = "algorithm"
    PROTOCOL_KEY = "protocol"
    PORT_KEY = "port"
    SESSION_PERSISTENCE_KEY = "session_persistence"
    HEALTH_MONITOR_KEY = "health_monitor"
    POOL_MEMBER_KEY = "pool_members"

    ALGORITHM_MAP = {
        "ROUNDROBIN": "round_robin",
        "LEASTCONNECTION": "least_connections",
        "WEIGHTED_RR": "weighted_round_robin"
    }

    def __init__(
            self,
            port,
            protocol,
            algorithm,
            session_persistence=None,
            health_monitor=None,
            pool_members=None,
    ):
        self.port = port
        self.protocol = protocol
        self.algorithm = algorithm
        self.session_persistence = session_persistence
        self.health_monitor = health_monitor
        self.pool_members = pool_members or list()

    def to_json(self):
        return {
            self.PROTOCOL_KEY: self.protocol,
            self.PORT_KEY: self.port,
            self.ALGORITHM_KEY: self.algorithm,
            self.SESSION_PERSISTENCE_KEY: self.session_persistence,
            self.HEALTH_MONITOR_KEY: self.health_monitor.to_json()
            if self.health_monitor
            else None,
            self.POOL_MEMBER_KEY: [
                pool_member.to_json() for pool_member in self.pool_members
            ],
        }

    def to_ibm(self):
        ibm_pool = IBMPool(
            "{}-{}-pool".format(self.protocol.lower(), self.port),
            self.ALGORITHM_MAP[self.algorithm],
            self.protocol.lower(),
            self.session_persistence,
        )

        for pool_member in self.pool_members:
            ibm_pool.pool_members.append(pool_member.to_ibm())

        if self.health_monitor:
            ibm_pool.health_check = self.health_monitor.to_ibm()

        return ibm_pool


class SoftLayerPoolHealthMonitor(object):
    MAX_RETRIES_KEY = "max_retries"
    INTERVAL_KEY = "interval"
    TIMEOUT_KEY = "timeout"
    MONITOR_TYPE_KEY = "monitor_type"
    URL_PATH_KEY = "url_path"

    def __init__(self, max_retries, timeout, monitor_type, url_path, interval):
        self.max_retries = max_retries
        self.timeout = timeout
        self.monitor_type = monitor_type
        self.url_path = url_path
        self.interval = interval

    def to_json(self):
        return {
            self.MAX_RETRIES_KEY: self.max_retries,
            self.INTERVAL_KEY: self.interval,
            self.TIMEOUT_KEY: self.timeout,
            self.MONITOR_TYPE_KEY: self.monitor_type,
            self.URL_PATH_KEY: self.url_path,
        }

    def to_ibm(self):
        return IBMHealthCheck(
            delay=self.interval,
            max_retries=self.max_retries,
            timeout=self.timeout,
            type_=self.monitor_type.lower(),
            url_path=self.url_path,
            port=80,
        )


class SoftLayerPoolMember(object):
    WEIGHT_KEY = "weight"
    IP_KEY = "ip"
    INSTANCE_KEY = "instance"
    PORT_KEY = "port"

    def __init__(self, weight, port, ip, instance=None):
        self.weight = weight
        self.ip = ip
        self.port = port
        self.instance = instance

    def to_json(self):
        return {
            self.WEIGHT_KEY: self.weight,
            self.IP_KEY: self.ip,
            self.INSTANCE_KEY: self.instance.to_json() if self.instance else None,
        }

    def to_ibm(self):
        ibm_pool_member = IBMPoolMember(self.port, self.weight)
        if self.instance:
            ibm_pool_member.instance = self.instance.to_ibm()

        return ibm_pool_member


class SoftLayerSecurityGroup(object):
    NAME_KEY = "name"
    DEFAULT_KEY = "default"
    RULE_KEY = "rules"

    def __init__(self, name, is_default=False, rules=None):
        self.name = name
        self.is_default = is_default
        self.rules = rules or list()

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.DEFAULT_KEY: self.is_default,
            self.RULE_KEY: [rule.to_json() for rule in self.rules],
        }

    def to_ibm(self):
        ibm_security_group = IBMSecurityGroup(
            name=transform_ibm_name(self.name), region="dummy-region", status=CREATION_PENDING)
        if self.rules:
            ibm_security_group.rules = [rule.to_ibm() for rule in self.rules]

        return ibm_security_group

    @classmethod
    def from_softlayer_json(cls, security_group):
        sl_security_group = cls(security_group["securityGroup"]["name"])
        for rule in security_group["securityGroup"].get("rules", []):
            if rule["ethertype"] == "IPv6":
                continue

            sl_security_group_rule = SoftLayerSecurityGroupRule.from_softlayer_json(rule_json=rule)
            sl_security_group.rules.append(sl_security_group_rule)

        return sl_security_group


class SoftLayerSecurityGroupRule(object):
    ID_KEY = "id"
    RESOURCE_ID_KEY = "resource_id"
    DIRECTION_KEY = "direction"
    PROTOCOL_KEY = "protocol"
    PORT_MAX_KEY = "port_max"
    PORT_MIN_KEY = "port_min"
    CIDR_BLOCK_KEY = "cidr_block"
    SECURITY_GROUP_KEY = "security_group"
    RULE_TYPE_KEY = "rule_type"
    ADDRESS_KEY = "address"
    CODE_KEY = "code"
    TYPE_KEY = "type"

    def __init__(
            self,
            direction,
            protocol=None,
            code=None,
            type_=None,
            port_min=None,
            port_max=None,
            address=None,
            cidr_block=None,
            rule_type=None,
    ):
        self.direction = direction
        self.protocol = protocol
        self.port_max = port_max
        self.port_min = port_min
        self.cidr_block = cidr_block
        self.address = address
        self.code = code
        self.type = type_
        self.rule_type = rule_type or "any"

    def to_json(self):
        return {
            self.DIRECTION_KEY: self.direction,
            self.PROTOCOL_KEY: self.protocol,
            self.PORT_MAX_KEY: self.port_max,
            self.PORT_MIN_KEY: self.port_min,
            self.RULE_TYPE_KEY: self.rule_type,
            self.CIDR_BLOCK_KEY: self.cidr_block,
            self.ADDRESS_KEY: self.address,
            self.CODE_KEY: self.code,
            self.TYPE_KEY: self.type,
        }

    def to_ibm(self):
        if self.direction == "egress":
            self.direction = "outbound"
        elif self.direction == "ingress":
            self.direction = "inbound"

        ibm_sec_group_rule = IBMSecurityGroupRule(
            self.direction,
            self.protocol,
            self.code,
            self.type,
            self.port_min,
            self.port_min,
            self.address if not is_private_ip(self.address) else "0.0.0.0/0",
            self.cidr_block if not is_private_ip(self.cidr_block) else "0.0.0.0/0",
            self.rule_type,
        )

        return ibm_sec_group_rule

    @classmethod
    def from_softlayer_json(cls, rule_json):
        return cls(direction=rule_json["direction"], protocol=rule_json.get("protocol", "all"),
                   port_max=rule_json.get("portRangeMax"), port_min=rule_json.get("portRangeMin"),
                   address=rule_json["primaryIpAddress"])


class SoftLayerSubnet(object):
    VIF_ID_KEY = "vif_id"
    ADDRESS_KEY = "address"
    NETWORK_KEY = "network"
    NAME_KEY = "name"
    INTERFACE_KEY = "interface_name"
    PUBLIC_GATEWAY_KEY = "public_gateway"
    FIREWALLS = "firewalls"
    NETWORK_ID_KEY = "network_id"

    def __init__(self, name, vif_id, address=None, network=None, interface=None, public_gateway=False, firewalls=None,
                 network_id=None):
        self.name = name
        self.vif_id = vif_id
        self.address = address
        self.network = network or get_network(address)
        self.interface = interface
        self.public_gateway = public_gateway
        self.firewalls = firewalls or list()
        self.network_id = network_id

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.VIF_ID_KEY: self.vif_id,
            self.ADDRESS_KEY: self.address,
            self.NETWORK_KEY: self.network,
            self.INTERFACE_KEY: self.interface,
            self.PUBLIC_GATEWAY_KEY: self.public_gateway,
            self.FIREWALLS: [firewall.to_json() for firewall in self.firewalls] if self.firewalls else [],
            self.NETWORK_ID_KEY: self.network_id
        }

    def to_ibm(self):
        ibm_subnet = IBMSubnet(
            name=transform_ibm_name(self.name), zone="dummy-zone", ipv4_cidr_block=self.network,
            region="dummy-region", status=CREATION_PENDING)

        if self.firewalls:
            network_acl = IBMNetworkAcl("acl-{}".format(self.name), "dummy-region")

            for firewall in self.firewalls:
                if not firewall.list_port_action_protocol_rules():
                    continue

                for rule in firewall.list_port_action_protocol_rules():
                    ibm_rules = rule.to_ibm(firewall.name)
                    for rule_ in ibm_rules:
                        network_acl.add_rule(rule_)

            ibm_subnet.network_acl = network_acl
        return ibm_subnet


class SoftLayerFirewall(object):
    NAME_KEY = "name"
    RULES_KEY = "rules"
    DIRECTION_KEY = "direction"
    PORTS_KEY = "ports"

    def __init__(
            self,
            name,
            direction=None,
            rules=None,
            vif_id=None,
            source_addresses=None,
            destination_addresses=None,
    ):
        self.name = name
        self.direction = direction
        self.rules = rules or list()
        self.source_addresses = source_addresses or list()
        self.destination_addresses = destination_addresses or list()
        self.vif_id = vif_id

    def to_json(self):
        rules_list = list()
        json_data = {
            self.NAME_KEY: self.name,
            self.DIRECTION_KEY: self.direction
        }
        if self.list_port_action_protocol_rules():
            for rule in self.list_port_action_protocol_rules():
                rules_list.append(rule.to_json())

            json_data[self.RULES_KEY] = rules_list

        return json_data

    def list_unique_ports(self):
        unique_ports = {
            'source_ports': [],
            'destination_ports': [],
            'hybrid_ports': {
                'source': [],
                'destination': []
            }
        }

        for rule in self.rules:
            if rule.list_source_ports() and not rule.list_destination_ports():
                unique_ports['source_ports'].extend(rule.list_source_ports())
            if not rule.list_source_ports() and rule.list_destination_ports():
                unique_ports['destination_ports'].extend(rule.list_destination_ports())
            if rule.list_hybrid_ports().get('source_ports') and rule.list_hybrid_ports()['destination_ports']:
                unique_ports['hybrid_ports']['source'].extend(set(rule.list_hybrid_ports()['source_ports']))
                unique_ports['hybrid_ports']['destination'].extend(rule.list_hybrid_ports()['destination_ports'])

        unique_ports['source_ports'] = remove_duplicates(unique_ports['source_ports'])
        unique_ports['destination_ports'] = remove_duplicates(unique_ports['destination_ports'])
        unique_ports['hybrid_ports']['source'] = remove_duplicates(unique_ports['hybrid_ports']['source'])
        unique_ports['hybrid_ports']['destination'] = remove_duplicates(unique_ports['hybrid_ports']['destination'])

        return unique_ports

    def list_source_rules(self):
        source_rules = list()

        for rule in self.rules:
            if rule.list_source_ports() and not rule.list_destination_ports():
                source_rules.append(rule)
        return source_rules

    def list_destination_rules(self):
        destination_rules = list()

        for rule in self.rules:
            if rule.list_destination_ports() and not rule.list_source_ports():
                destination_rules.append(rule)
        return destination_rules

    def list_allow_all_rules(self):
        allow_all_rules = list()

        for rule in self.rules:
            if rule.is_allow_to_all_ports():
                allow_all_rules.append(rule)

        return allow_all_rules

    def list_hybrid_rules(self):
        hybrid_rules = list()

        for rule in self.rules:
            if rule.list_hybrid_ports()['source_ports'] and rule.list_hybrid_ports()['destination_ports']:
                hybrid_rules.append(rule)

        return hybrid_rules

    def list_unique_src_port_action_protocol(self):
        src_unique_list = list()
        for rule in self.list_source_rules():
            if rule.list_source_ports() and not rule.list_destination_ports():
                for port in rule.list_source_ports():
                    if {
                        'port': port, 'action': rule.action, 'protocol': rule.protocol
                    } not in src_unique_list:
                        src_unique_list.append({
                            'port': port,
                            'action': rule.action,
                            'protocol': rule.protocol
                        })

        return src_unique_list

    def list_unique_dest_port_action_protocol(self):
        dest_unique_list = list()
        for rule in self.list_destination_rules():
            if rule.list_destination_ports() and not rule.list_source_ports():
                for port in rule.list_destination_ports():
                    if {
                        'port': port, 'action': rule.action, 'protocol': rule.protocol
                    } not in dest_unique_list:
                        dest_unique_list.append({
                            'port': port,
                            'action': rule.action,
                            'protocol': rule.protocol
                        })

        return dest_unique_list

    def list_unique_allow_all_port_action_protocol(self):
        allow_all_unique_list = list()
        for rule in self.list_allow_all_rules():
            if rule.is_allow_to_all_ports():
                if {
                    'port': 'ANY', 'action': rule.action, 'protocol': rule.protocol
                } not in allow_all_unique_list:
                    allow_all_unique_list.append({
                        'port': 'ANY',
                        'action': rule.action,
                        'protocol': rule.protocol
                    })
        return allow_all_unique_list

    def list_unique_hybrid_port_action_protocol(self):
        hybrid_unique_list = list()
        for rule in self.list_hybrid_rules():
            if rule.list_hybrid_ports():
                for src_port, dest_port in zip(rule.list_hybrid_ports()['source_ports'],
                                               rule.list_hybrid_ports()['destination_ports']):
                    if {
                        'src_port': src_port, 'dest_port': dest_port, 'action': rule.action, 'protocol': rule.protocol
                    } not in hybrid_unique_list:
                        hybrid_unique_list.append({
                            'src_port': src_port,
                            'dest_port': dest_port,
                            'action': rule.action,
                            'protocol': rule.protocol
                        })
        return hybrid_unique_list

    def list_port_action_protocol_rules(self):
        sequence = set()
        rules_list = {
            'source_rules': [],
            'destination_rules': [],
            'allow_all_rules': [],
            'hybrid_rules': []
        }
        for src_data in self.list_unique_src_port_action_protocol():
            src_data['rules'] = list()
            for rule in self.list_source_rules():
                if src_data['port'] in rule.list_source_ports() \
                        and src_data.get('protocol') == rule.protocol \
                        and src_data.get('action') == rule.action:
                    if src_data not in rules_list.get('source_rules'):
                        src_data['rules'].append(rule)
                        sequence.add(rule)
                        rules_list['source_rules'].append(src_data)

        for dest_data in self.list_unique_dest_port_action_protocol():
            dest_data['rules'] = list()
            for rule in self.list_destination_rules():
                if dest_data['port'] in rule.list_destination_ports() \
                        and dest_data.get('protocol') == rule.protocol \
                        and dest_data.get('action') == rule.action:
                    if dest_data not in rules_list.get('destination_rules'):
                        dest_data['rules'].append(rule)
                        sequence.add(rule)
                        rules_list['destination_rules'].append(dest_data)

        for allow_all_data in self.list_unique_allow_all_port_action_protocol():
            allow_all_data['rules'] = list()
            for rule in self.list_allow_all_rules():
                if rule.is_allow_to_all_ports() \
                        and allow_all_data.get('protocol') == rule.protocol \
                        and allow_all_data.get('action') == rule.action:
                    if allow_all_data not in rules_list.get('allow_all_rules'):
                        allow_all_data['rules'].append(rule)
                        sequence.add(rule)
                        rules_list['allow_all_rules'].append(allow_all_data)

        for hybrid_data in self.list_unique_hybrid_port_action_protocol():
            hybrid_data['rules'] = list()
            for rule in self.list_hybrid_rules():
                if (hybrid_data['src_port'], hybrid_data['dest_port']) in zip(rule.list_hybrid_ports()['source_ports'],
                                                                              rule.list_hybrid_ports()[
                                                                                  'destination_ports']) \
                        and hybrid_data.get('protocol') == rule.protocol \
                        and hybrid_data.get('action') == rule.action:
                    if hybrid_data not in rules_list.get('hybrid_rules'):
                        hybrid_data['rules'].append(rule)
                        sequence.add(rule)
                        rules_list['hybrid_rules'].append(hybrid_data)

        return sorted(sequence, key=lambda x: x.rule_no)

    def list_port_based_rules(self, src_port=None, dest_port=None):
        port_based_rules = []
        for rule in self.rules:
            if src_port in rule.list_source_ports() and dest_port is None:
                port_based_rules.append(rule)

            if dest_port in rule.list_destination_ports() and src_port is None:
                port_based_rules.append(rule)

            if (src_port, dest_port) in zip(rule.list_hybrid_ports()['source_ports'],
                                            rule.list_hybrid_ports()['destination_ports']):
                port_based_rules.append(rule)

        return port_based_rules

    def get_private_source_addresses(self, rules=None):
        private_source_addresses = []
        if rules is None:
            return

        for rule in rules:
            if rule.list_private_source_addresses():
                private_source_addresses.extend(rule.list_private_source_addresses())

        return private_source_addresses

    def get_public_source_addresses(self, rules=None):
        public_source_addresses = []
        for rule in rules:
            if rule.list_public_source_addresses():
                public_source_addresses.extend(rule.list_public_source_addresses())

        return public_source_addresses

    def get_private_destination_addresses(self, rules=None):
        private_destination_addresses = []
        for rule in rules:
            if rule.list_private_destination_addresses():
                private_destination_addresses.extend(rule.list_private_destination_addresses())

        return private_destination_addresses

    def get_public_destination_addresses(self, rules=None):
        public_destination_addresses = []
        for rule in rules:
            if rule.list_public_destination_addresses():
                public_destination_addresses.extend(rule.list_public_destination_addresses())

        return public_destination_addresses

    def list_source_addresses(self, rules=None):
        source_addresses = []
        source_addresses.extend(self.get_private_source_addresses(rules))
        source_addresses.extend(self.get_public_source_addresses(rules))
        return source_addresses

    def list_destination_addresses(self, rules=None):
        destination_addresses = []
        destination_addresses.extend(self.get_private_destination_addresses(rules))
        destination_addresses.extend(self.get_public_destination_addresses(rules))
        return destination_addresses

    def to_firewall_json(self):
        source_rules = []
        destination_rules = []
        hybrid_rules = []

        for src_port in self.list_unique_ports()['source_ports']:
            port_based_src_rules = self.list_port_based_rules(src_port=src_port)

            data = {
                'port': src_port,
                'rules': sorted(self.get_rules_count(port_based_src_rules), key=lambda x: x['rule_number']),
                'source_addresses': self.list_source_addresses(port_based_src_rules),
                'destination_addresses': self.list_destination_addresses(port_based_src_rules)
            }
            source_rules.append(data)

        for dest_port in self.list_unique_ports()['destination_ports']:
            port_based_dest_rules = self.list_port_based_rules(dest_port=dest_port)

            data = {
                'port': dest_port,
                'rules': sorted(self.get_rules_count(port_based_dest_rules), key=lambda x: x['rule_number']),
                'source_addresses': self.list_source_addresses(port_based_dest_rules),
                'destination_addresses': self.list_destination_addresses(port_based_dest_rules)
            }
            destination_rules.append(data)

        for src_port, dest_port in zip(self.list_unique_ports()['hybrid_ports']['source'],
                                       self.list_unique_ports()['hybrid_ports']['destination']):
            port_based_hybrid_rules = self.list_port_based_rules(src_port=src_port,
                                                                 dest_port=dest_port)

            data = {
                'port': f"{src_port}/{dest_port}",
                'rules': sorted(self.get_rules_count(port_based_hybrid_rules), key=lambda x: x['rule_number']),
                'source_addresses': self.list_source_addresses(port_based_hybrid_rules),
                'destination_addresses': self.list_destination_addresses(port_based_hybrid_rules)
            }
            hybrid_rules.append(data)

        all_protocol = [{
            "port": "any",
            'rules': sorted(self.get_rules_count(self.list_allow_all_rules()), key=lambda x: x['rule_number']),
            'source_addresses': self.list_source_addresses(self.list_allow_all_rules()),
            'destination_addresses': self.list_destination_addresses(self.list_allow_all_rules())
        }]

        data = {
            'firewall_name': f"{self.name}(vif_{self.vif_id})",
            'source_ports': source_rules,
            'destination_ports': destination_rules,
            'hybrid_ports': hybrid_rules,
            'all_protocols': all_protocol
        }

        return data

    def get_rules_count(self, rules=None):

        rules_count = []

        for rule in rules:
            if {
                'rule_number': rule.rule_no,
                'action': rule.action,
                'protocol': rule.protocol,
            } not in rules_count:
                rules_count.append({
                    'rule_number': rule.rule_no,
                    'action': rule.action,
                    'protocol': rule.protocol,
                    'translated_rule': rule.to_ibm(self.name)[0].to_json()
                })
        return rules_count

    def to_ibm(self, vpc=None):
        ibm_acl = IBMNetworkAcl(transform_ibm_name(self.name), status=CREATION_PENDING)
        ibm_acl.ibm_vpc_network = vpc

        if self.list_port_action_protocol_rules():
            for source in self.list_port_action_protocol_rules().get('source_rules'):
                ibm_acl.rules.extend(source['rules'][0].to_ibm(self.name))

            for allow_all in self.list_port_action_protocol_rules().get('allow_all_rules'):
                ibm_acl.rules.extend(allow_all['rules'][0].to_ibm(self.name))

            for destination in self.list_port_action_protocol_rules().get('destination_rules'):
                ibm_acl.rules.extend(destination['rules'][0].to_ibm(self.name))

            for hybrid in self.list_port_action_protocol_rules().get('hybrid_rules'):
                ibm_acl.rules.extend(hybrid['rules'][0].to_ibm(self.name))

        return ibm_acl


class SoftLayerFirewallRule(object):
    RULE_NO_KEY = "rule"
    PROTOCOL_KEY = "protocol"
    ACTION_KEY = "action"
    DIRECTION_KEY = "direction"
    DESTINATION_ADDRESS_KEY = "destination_addresses"
    SOURCE_ADDRESS_KEY = "source_addresses"
    DESTINATION_ADDRESS_GROUPS_KEY = "destination_address_groups"
    SOURCE_ADDRESS_GROUPS_KEY = "source_address_groups"
    DESTINATION_PORT_KEY = "destination_ports"
    SOURCE_PORT_KEY = "source_ports"
    DESTINATION_PORT_GROUPS_KEY = "destination_port_groups"
    SOURCE_PORT_GROUPS_KEY = "source_port_groups"
    PRIVATE_KEY = "is_private"

    def __init__(
            self,
            rule_no,
            protocol=None,
            action=None,
            code=None,
            type=None,
            description=None,
            destination_addresses=None,
            source_addresses=None,
            destination_ports=None,
            source_ports=None,
            destination_address_groups=None,
            source_address_groups=None,
            destination_port_groups=None,
            source_port_groups=None,
            direction=None,
            is_private=False,
    ):
        self.rule_no = rule_no
        self.protocol = protocol or "all"
        self.direction = direction
        self.action = action
        self.code = code
        self.type = type
        self.description = description
        self.destination_addresses = destination_addresses or list()
        self.source_addresses = source_addresses or list()
        self.destination_ports = destination_ports or list()
        self.source_ports = source_ports or list()
        self.source_address_groups = source_address_groups or list()
        self.destination_address_groups = destination_address_groups or list()
        self.destination_port_groups = destination_port_groups or list()
        self.source_port_groups = source_port_groups or list()
        self.is_private = is_private

    def to_json(self):
        json_data = {
            self.RULE_NO_KEY: self.rule_no,
            self.PROTOCOL_KEY: self.protocol,
            self.DIRECTION_KEY: self.direction,
            self.ACTION_KEY: self.action,
            self.DESTINATION_ADDRESS_KEY: self.destination_addresses,
            self.SOURCE_ADDRESS_KEY: self.source_addresses,
            self.DESTINATION_PORT_KEY: [
                address for address in self.destination_ports
            ] if self.destination_ports else [],
            self.SOURCE_PORT_KEY: [address for address in self.source_ports] if self.source_ports else [],
            self.DESTINATION_ADDRESS_GROUPS_KEY: [
                address.to_json() for address in self.destination_address_groups
            ] if self.destination_address_groups else [],
            self.SOURCE_ADDRESS_GROUPS_KEY: [
                address.to_json() for address in self.source_address_groups
            ] if self.source_address_groups else [],
            self.DESTINATION_PORT_GROUPS_KEY: [
                port.to_json() for port in self.destination_port_groups
            ] if self.destination_port_groups else [],
            self.SOURCE_PORT_GROUPS_KEY: [
                port.to_json() for port in self.source_port_groups
            ] if self.source_port_groups else [],
        }

        return json_data

    def list_source_ports(self):
        src_port_list = list()

        if self.source_port_groups and not self.destination_port_groups:
            for source_port in self.source_port_groups:
                src_port_list.extend(source_port.ports)

        if self.source_ports and not self.destination_ports:
            src_port_list.extend(self.source_ports)
        return set(src_port_list)

    def list_destination_ports(self):
        dest_port_list = list()

        if self.destination_port_groups and not self.source_port_groups:
            for dest_port in self.destination_port_groups:
                dest_port_list.extend(dest_port.ports)

        if self.destination_ports and not self.source_ports:
            dest_port_list.extend(self.destination_ports)

        return set(dest_port_list)

    def is_allow_to_all_ports(self):
        if not (len(self.list_source_ports()) and len(self.list_destination_ports())) and self.protocol == 'all':
            return True

        return False

    def list_hybrid_ports(self):
        hybrid_ports = {
            'source_ports': [],
            'destination_ports': []
        }
        if self.source_port_groups and self.destination_port_groups:
            for source_port, destination_port in zip(self.source_port_groups, self.destination_port_groups):
                hybrid_ports['source_ports'].extend(source_port.ports)
                hybrid_ports['destination_ports'].extend(destination_port.ports)

        if self.source_ports and self.destination_ports:
            for source_port, destination_port in zip(self.source_ports, self.destination_ports):
                hybrid_ports['source_ports'].append(source_port)
                hybrid_ports['destination_ports'].append(destination_port)

        return hybrid_ports

    def list_source_addresses(self):
        source_address_list = list()
        source_address_list.extend(self.source_addresses)
        for add_grp in self.source_address_groups:
            source_address_list.extend(add_grp.addresses)
        return source_address_list

    def list_destination_addresses(self):
        destination_address_list = list()
        destination_address_list.extend(self.destination_addresses)
        for add_grp in self.destination_address_groups:
            destination_address_list.extend(add_grp.addresses)

        return destination_address_list

    def list_private_source_addresses(self):
        if self.list_source_addresses():
            private_src_addresses = [src_add for src_add in self.list_source_addresses() if is_private(src_add)]
            return private_src_addresses

    def list_public_source_addresses(self):
        if self.list_source_addresses():
            public_src_addresses = [src_add for src_add in self.list_source_addresses() if not is_private(src_add)]
            return public_src_addresses

    def list_private_destination_addresses(self):
        if self.list_destination_addresses():
            private_dest_addresses = [dest_add for dest_add in self.list_destination_addresses() if
                                      is_private(dest_add)]
            return private_dest_addresses

    def list_public_destination_addresses(self):
        if self.list_destination_addresses():
            public_dest_addresses = [dest_add for dest_add in self.list_destination_addresses() if
                                     not is_private(dest_add)]
            return public_dest_addresses

    def is_private_rule(self):
        if len(self.source_addresses) or len(self.destination_addresses):
            for address in self.source_addresses + self.destination_addresses:
                if not is_private(address):
                    return False
        if len(self.source_address_groups) or len(self.destination_address_groups):
            for address in self.source_address_groups + self.destination_address_groups:
                if not address.is_private_address_group:
                    return False

        self.is_private = True
        return True

    def to_ibm(self, name=None):
        name = transform_ibm_name(name)
        acl_rules_list = list()
        rule_count = 1
        action = "allow" if self.action == "accept" else "deny"

        destination_ports_list, source_ports_list = list(), list()

        # Destination Ports Groups
        if self.destination_port_groups:
            for dest_port_group in self.destination_port_groups:
                destination_ports_list.extend(dest_port_group.ports)
        # Source Ports Groups
        if self.source_port_groups:
            for source_port_group in self.source_port_groups:
                source_ports_list.extend(source_port_group.ports)

        # Destination Ports Groups
        if self.destination_ports:
            destination_ports_list.extend(self.destination_ports)

        # Source Ports
        if self.source_ports:
            source_ports_list.extend(self.source_ports)

        if not source_ports_list:
            for destination_port in destination_ports_list:
                destination_port_min = destination_port_max = destination_port
                if "-" in destination_port:
                    destination_port = destination_port.split("-")
                    destination_port_min = destination_port[0]
                    destination_port_max = destination_port[1]

                if self.list_public_destination_addresses() and len(self.list_public_destination_addresses()):
                    for dest_add in self.list_public_destination_addresses():
                        acl_rule = IBMNetworkAclRule(
                            "{}-rule-{}-{}".format(name, self.rule_no, rule_count),
                            action,
                            direction=self.direction,
                            protocol=self.protocol or "all",
                            type_=self.type if self.protocol == "icmp" else None,
                            code=self.code if self.protocol == "icmp" else None,
                            source="0.0.0.0/0",
                            destination=dest_add,
                            port_min=int(destination_port_min),
                            port_max=int(destination_port_max),
                        )
                        rule_count = rule_count + 1
                        acl_rules_list.append(acl_rule)
                else:
                    acl_rule = IBMNetworkAclRule(
                        "{}-rule-{}-{}".format(name, self.rule_no, rule_count),
                        action,
                        direction=self.direction,
                        protocol=self.protocol or "all",
                        type_=self.type if self.protocol == "icmp" else None,
                        code=self.code if self.protocol == "icmp" else None,
                        source="0.0.0.0/0",
                        destination="0.0.0.0/0",
                        port_min=int(destination_port_min),
                        port_max=int(destination_port_max),
                    )
                    rule_count = rule_count + 1
                    acl_rules_list.append(acl_rule)

        if not destination_ports_list:
            for source_port in source_ports_list:
                source_port_min = source_port_max = source_port
                if "-" in source_port:
                    source_port = source_port.split("-")
                    source_port_min = source_port[0]
                    source_port_max = source_port[1]
                if self.list_public_destination_addresses() and len(self.list_public_destination_addresses()):
                    for dest_add in self.list_public_destination_addresses():
                        acl_rule = IBMNetworkAclRule(
                            "{}-rule-{}-{}".format(name, self.rule_no, rule_count),
                            action,
                            direction=self.direction,
                            protocol=self.protocol or "all",
                            type_=self.type if self.protocol == "icmp" else None,
                            code=self.code if self.protocol == "icmp" else None,
                            source="0.0.0.0/0",
                            destination=dest_add or "0.0.0.0/0",
                            source_port_min=int(source_port_min),
                            source_port_max=int(source_port_max),
                        )
                        rule_count = rule_count + 1
                        acl_rules_list.append(acl_rule)
                else:
                    acl_rule = IBMNetworkAclRule(
                        "{}-rule-{}-{}".format(name, self.rule_no, rule_count),
                        action,
                        direction=self.direction,
                        protocol=self.protocol or "all",
                        type_=self.type if self.protocol == "icmp" else None,
                        code=self.code if self.protocol == "icmp" else None,
                        source="0.0.0.0/0",
                        destination="0.0.0.0/0",
                        source_port_min=int(source_port_min),
                        source_port_max=int(source_port_max),
                    )
                    rule_count = rule_count + 1
                    acl_rules_list.append(acl_rule)

        else:
            for source_port in source_ports_list:
                source_port_min = source_port_max = source_port
                if "-" in source_port:
                    source_port = source_port.split("-")
                    source_port_min = source_port[0]
                    source_port_max = source_port[1]

                for destination_port in destination_ports_list:
                    destination_port_min = destination_port_max = destination_port
                    if "-" in destination_port:
                        destination_port = destination_port.split("-")
                        destination_port_min = destination_port[0]
                        destination_port_max = destination_port[1]

                    if self.list_public_destination_addresses() and len(self.list_public_destination_addresses()):
                        for dest_add in self.list_public_destination_addresses():
                            acl_rule = IBMNetworkAclRule(
                                "{}-rule-{}-{}".format(name, self.rule_no, rule_count),
                                action,
                                direction=self.direction,
                                protocol=self.protocol or "all",
                                type_=self.type if self.protocol == "icmp" else None,
                                code=self.code if self.protocol == "icmp" else None,
                                source="0.0.0.0/0",
                                destination=dest_add,
                                source_port_min=int(source_port_min),
                                source_port_max=int(source_port_max),
                                port_min=int(destination_port_min),
                                port_max=int(destination_port_max),
                            )
                            rule_count = rule_count + 1
                            acl_rules_list.append(acl_rule)

                    else:
                        acl_rule = IBMNetworkAclRule(
                            "{}-rule-{}-{}".format(name, self.rule_no, rule_count),
                            action,
                            direction=self.direction,
                            protocol=self.protocol or "all",
                            type_=self.type if self.protocol == "icmp" else None,
                            code=self.code if self.protocol == "icmp" else None,
                            source="0.0.0.0/0",
                            destination="0.0.0.0/0",
                            source_port_min=int(source_port_min),
                            source_port_max=int(source_port_max),
                            port_min=int(destination_port_min),
                            port_max=int(destination_port_max),
                        )
                        rule_count = rule_count + 1
                        acl_rules_list.append(acl_rule)

        if not acl_rules_list:
            acl_rule = IBMNetworkAclRule(
                "{}-rule-{}-{}".format(name, self.rule_no, rule_count),
                action,
                direction=self.direction,
                protocol=self.protocol or "all",
                source="0.0.0.0/0",
                destination="0.0.0.0/0",
            )
            acl_rules_list.append(acl_rule)

        return acl_rules_list


class SoftLayerAddressGroup(object):
    NAME_KEY = "name"
    ADDRESSES_KEY = "addresses"
    PRIVATE_KEY = "is_private"

    def __init__(self, name, addresses=None):
        self.name = name
        self.addresses = addresses or list()

    def to_json(self):
        return {self.NAME_KEY: self.name, self.ADDRESSES_KEY: self.addresses}

    @property
    def is_private_address_group(self):
        if len(self.addresses):
            return all([is_private(address) for address in self.addresses])


class SoftLayerPortGroup(object):
    NAME_KEY = "name"
    PORTS_KEY = "ports"

    def __init__(self, name, ports=None):
        self.name = name
        self.ports = ports or list()

    def to_json(self):
        return {self.NAME_KEY: self.name, self.PORTS_KEY: self.ports}


class SoftLayerIpsec(object):
    NAME_KEY = "name"
    PRE_SHARED_SECRET_KEY = "pre_shared_secret"
    PEER_ADDRESS = "peer_address"
    ESP_GROUP_KEY = "esp_group"
    IKE_GROUP_KEY = "ike_group"
    TUNNELS_KEY = "tunnels"

    def __init__(
            self,
            peer_address,
            pre_shared_secret=None,
            esp_group=None,
            ike_group=None,
            tunnels=None,
    ):
        self.name = "vpn-{}".format("-".join(peer_address.split(".")))
        self.pre_shared_secret = pre_shared_secret
        self.peer_address = peer_address
        self.esp_group = esp_group
        self.ike_group = ike_group
        self.tunnels = tunnels

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.PRE_SHARED_SECRET_KEY: self.pre_shared_secret,
            self.PEER_ADDRESS: self.peer_address,
            self.ESP_GROUP_KEY: self.esp_group.to_json() if self.esp_group else None,
            self.IKE_GROUP_KEY: self.ike_group.to_json() if self.ike_group else None,
            self.TUNNELS_KEY: [tunnel.to_json() for tunnel in self.tunnels]
            if self.tunnels
            else [],
        }

    def to_ibm(self):
        vpn_gateway = IBMVpnGateway(
            transform_ibm_name(self.name), "dummy-region", status=CREATION_PENDING
        )
        vpn_connection = IBMVpnConnection(
            name=transform_ibm_name(self.name),
            peer_address=self.peer_address,
            pre_shared_key=self.pre_shared_secret,
            local_cidrs=[],
            discovered_local_cidrs=(
                [tunnel.discovered_local_cidrs for tunnel in self.tunnels if tunnel.discovered_local_cidrs]
                if self.tunnels else []
            ),
            peer_cidrs=json.dumps(
                [tunnel.remote_subnet for tunnel in self.tunnels if tunnel.remote_subnet]
                if self.tunnels
                else []
            ),
            dpd_interval=self.ike_group.dpd_interval,
            dpd_timeout=self.ike_group.dpd_timeout,
            dpd_action=self.ike_group.dpd_action,
        )
        vpn_connection.ibm_ike_policy = (
            self.ike_group.to_ibm() if self.ike_group else None
        )
        vpn_connection.ibm_ipsec_policy = (
            self.esp_group.to_ibm() if self.esp_group else None
        )
        vpn_gateway.vpn_connections.append(vpn_connection)
        return vpn_gateway


class SoftLayerIpsecTunnel(object):
    TUNNEL_NO_KEY = "tunnel_no"
    LOCAL_SUBNET_KEY = "local_subnet"
    REMOTE_SUBNET_KEY = "remote_subnet"
    DISCOVERED_SUBNET = "discovered_local_cidrs"

    def __init__(self, tunnel_no, local_subnet=None, remote_subnet=None, discovered_local_cidrs=None):
        self.tunnel_no = tunnel_no
        self.local_subnet = local_subnet
        self.remote_subnet = remote_subnet
        self.discovered_local_cidrs = discovered_local_cidrs

    def to_json(self):
        return {
            self.TUNNEL_NO_KEY: self.tunnel_no,
            self.LOCAL_SUBNET_KEY: self.local_subnet,
            self.REMOTE_SUBNET_KEY: self.remote_subnet,
            self.DISCOVERED_SUBNET: self.discovered_local_cidrs
        }


class SoftLayerIkeGroup(object):
    NAME_KEY = "name"
    DH_GROUP_KEY = "dh-group"
    HASH_KEY = "hash"
    ENCRYPTION_KEY = "encryption"
    LIFETIME_KEY = "lifetime"
    IKE_VERSION = "ike_version"
    DPD_ACTION_KEY = "dpd_action"
    DPD_INTERVAL_KEY = "dpd_interval"
    DPD_TIMEOUT_KEY = "dpd_timeout"

    def __init__(
            self,
            name,
            lifetime="86400",
            dh_group=None,
            encryption=None,
            hash_=None,
            dpd_action="hold",
            dpd_interval="86400",
            dpd_timeout="86400",
    ):
        self.name = name
        self.lifetime = lifetime
        self.dh_group = dh_group
        self.encryption = encryption
        self.hash = hash_
        self.dpd_action = dpd_action
        self.dpd_interval = dpd_interval
        self.dpd_timeout = dpd_timeout

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.LIFETIME_KEY: self.lifetime,
            self.DH_GROUP_KEY: self.dh_group,
            self.ENCRYPTION_KEY: self.encryption,
            self.HASH_KEY: self.hash,
            self.DPD_ACTION_KEY: self.dpd_action,
            self.DPD_INTERVAL_KEY: self.dpd_interval,
            self.DPD_TIMEOUT_KEY: self.dpd_timeout,
        }

    def to_ibm(self):
        if self.encryption == "3des":
            self.encryption = "triple_des"

        return IBMIKEPolicy(
            name=transform_ibm_name(self.name),
            region="dummy-region",
            key_lifetime=int(self.lifetime),
            ike_version=2,
            authentication_algorithm=self.hash,
            encryption_algorithm=self.encryption,
            dh_group=int(self.dh_group) if self.dh_group else 2,
        )


class SoftLayerEspGroup(object):
    NAME_KEY = "name"
    HASH_KEY = "hash"
    ENCRYPTION_KEY = "encryption"
    LIFETIME_KEY = "lifetime"
    MODE_KEY = "mode"
    PFS_KEY = "pfs"

    def __init__(
            self,
            name,
            hash_=None,
            encryption=None,
            lifetime="86400",
            mode="tunnel",
            pfs="disabled",
    ):
        self.name = name
        self.hash = hash_
        self.encryption = encryption
        self.lifetime = lifetime
        self.mode = mode
        self.pfs = pfs

    def to_json(self):
        return {
            self.NAME_KEY: self.name,
            self.HASH_KEY: self.hash,
            self.ENCRYPTION_KEY: self.encryption,
            self.LIFETIME_KEY: self.lifetime,
            self.MODE_KEY: self.mode,
            self.PFS_KEY: self.pfs,
        }

    def to_ibm(self):
        if self.encryption == "3des":
            self.encryption = "triple_des"

        if "dh-group" in self.pfs:
            pfs_split = self.pfs.split("dh-group")
            self.pfs = "group_{}".format(pfs_split[-1])
        elif self.pfs == "enable":
            self.pfs = "group_2"

        return IBMIPSecPolicy(
            name=transform_ibm_name(self.name),
            region="dummy-region",
            key_lifetime=int(self.lifetime),
            authentication_algorithm=self.hash,
            encryption_algorithm=self.encryption,
            pfs_dh_group=self.pfs,
        )


class SoftLayerDedicatedHost:
    ID_KEY = "id"
    CPU_COUNT_KEY = "cpu_count"
    DISK_CAPACITY_KEY = "disk_capacity"
    MEMORY_CAPACITY_KEY = "memory_capacity"
    NAME_KEY = "name"
    DATACENTER_KEY = "datacenter"
    INSTANCES_KEY = "instances"

    def __init__(self, id, cpu_count, disk_capacity, memory_capacity, name, datacenter, instances):
        self.id = id
        self.cpu_count = cpu_count
        self.disk_capacity = disk_capacity
        self.memory_capacity = memory_capacity
        self.name = name
        self.datacenter = datacenter
        self.instances = instances

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.CPU_COUNT_KEY: self.cpu_count,
            self.DISK_CAPACITY_KEY: self.disk_capacity,
            self.MEMORY_CAPACITY_KEY: self.memory_capacity,
            self.NAME_KEY: self.name,
            self.DATACENTER_KEY: self.datacenter,
            self.INSTANCES_KEY: self.instances
        }

    @classmethod
    def from_softlayer_json(cls, dedicated_host_dict):
        return cls(
            id=dedicated_host_dict["id"],
            cpu_count=dedicated_host_dict["cpuCount"],
            disk_capacity=dedicated_host_dict["diskCapacity"],
            memory_capacity=dedicated_host_dict["memoryCapacity"],
            name=dedicated_host_dict["name"],
            datacenter=dedicated_host_dict["datacenter"].get("longName"),
            instances=[guest["id"] for guest in dedicated_host_dict["guests"]]
        )
