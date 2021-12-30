from doosra.common.utils import calculate_address_range, get_network
from doosra.migration.models import SoftLayerAddressGroup, SoftLayerEspGroup, SoftLayerFirewall, \
    SoftLayerFirewallRule, SoftLayerIkeGroup, SoftLayerIpsec, SoftLayerIpsecTunnel, SoftLayerPortGroup, SoftLayerSubnet


class Vyatta56Analyzer(object):
    PROTOCOL_IGNORE_LIST = ["udplite"]

    def __init__(self, configs):
        self.configs = configs.split("\n")

    def get_private_subnets(self):
        """
        Discover subnetworks from Vyatta5600 configs, in the format:
        set interfaces bonding <some-id> vif <some-id> address <address>
        Sample Configs:
        set interfaces bonding dp0bond0 vif 790 address '10.131.26.193/26'
        set interfaces bonding dp0bond0 vif 790 address '10.130.254.10/30'
        :return:
        """
        subnets_list = list()
        vif_id_list = list()
        for index, conf in enumerate(self.configs):
            if not conf.startswith("set interfaces bonding dp0bond0 "):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 8:
                continue

            if not (split_conf[4].strip() == "vif" and split_conf[6] == "address"):
                continue

            vif_id = split_conf[5].strip().strip("'")

            if vif_id not in vif_id_list:
                vif_id_list.append(vif_id)

            subnet_name = "subnet-{}-{}".format(split_conf[5], len([vif for vif in vif_id_list if vif == vif_id]))
            vyatta_subnet = SoftLayerSubnet(
                subnet_name, vif_id, split_conf[-1].strip().strip("'"), get_network(split_conf[-1].strip().strip("'")),
                split_conf[3].strip().strip("'"))

            if self.has_public_gateway(vyatta_subnet.network):
                vyatta_subnet.public_gateway = True

            if vyatta_subnet.name not in [subnet.name for subnet in subnets_list]:
                subnets_list.append(vyatta_subnet)

        for subnet in subnets_list:
            subnet.firewalls = self.get_attached_firewalls(subnet.vif_id)

        return subnets_list

    def get_attached_firewalls(self, vif_id):
        """
        Get attached firewalls with a VIF
        :return:
        """
        firewalls_list = list()
        for index, conf in enumerate(self.configs):
            if not conf.startswith(
                    "set interfaces bonding dp0bond0 vif {vif_id} firewall ".format(vif_id=vif_id)):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 9:
                continue

            if split_conf[7] == "out":
                firewall = self.get_firewalls(split_conf[8].strip("'"), "outbound", vif_id=vif_id)
                if firewall:
                    firewalls_list.append(firewall[0])

            elif split_conf[7] == "in":
                firewall = self.get_firewalls(split_conf[8].strip("'"), "inbound", vif_id=vif_id)
                if firewall:
                    firewalls_list.append(firewall[0])

        return firewalls_list

    def has_public_gateway(self, network):
        """
        We can assume that a subnet needs a public gateway if we find a specific NAT rule in Config File allowing the
        whole subnet to the internet and NATing it.
        Following are the commands for that NAT rule:
        set service nat source rule 100 outbound-interface 'dp0bond1'
        set service nat source rule 100 source address '192.168.100.0/30'
        set service nat source rule 100 translation address 'masquerade'
        :return:
        """
        rule_number = None
        for index, conf in enumerate(self.configs):
            if not conf.startswith("set service nat source rule "):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 9:
                continue

            if split_conf[6] == "source" and split_conf[7] == "address":
                if network == split_conf[8].strip("'") or self.get_address_groups(split_conf[8].strip("'")):
                    rule_number = split_conf[5].strip("'")
                    break

        if not rule_number:
            return

        interface_found, translation_found = False, False
        for index, conf in enumerate(self.configs):
            if conf.startswith("set service nat source rule {} outbound-interface 'dp0bond1'".format(rule_number)):
                interface_found = True
                break

        for index, conf in enumerate(self.configs):
            if conf.startswith("set service nat source rule {} translation address 'masquerade'".format(rule_number)):
                translation_found = True
                break

        if interface_found and translation_found:
            return True

    def get_esp_groups(self, name=None):
        """
        Get ESP Groups configured on v5600 device.
        Sample configs:
        set security vpn ipsec esp-group NetOrc_ESP_PROPOSAL compression 'disable'
        set security vpn ipsec esp-group NetOrc_ESP_PROPOSAL lifetime '86400'
        set security vpn ipsec esp-group NetOrc_ESP_PROPOSAL mode 'tunnel'
        set security vpn ipsec esp-group NetOrc_ESP_PROPOSAL pfs 'disable'
        set security vpn ipsec esp-group NetOrc_ESP_PROPOSAL proposal 1 encryption 'aes256'
        set security vpn ipsec esp-group NetOrc_ESP_PROPOSAL proposal 1 hash 'sha1'
        """
        esp_groups_list = list()
        for index, conf in enumerate(self.configs):
            if not conf.startswith("set security vpn ipsec esp-group "):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 8:
                continue

            esp_group_name = split_conf[5].strip()
            if name and name != esp_group_name:
                continue

            existing_esp_group = [esp_group for esp_group in esp_groups_list if esp_group.name == esp_group_name]
            esp_group = existing_esp_group[0] if existing_esp_group else SoftLayerEspGroup(esp_group_name)

            if split_conf[6] == "lifetime":
                esp_group.lifetime = split_conf[7].strip("'")

            elif split_conf[6] == "mode":
                esp_group.mode = split_conf[7].strip()

            elif split_conf[6] == "pfs":
                if split_conf[7].strip("'") == "disable":
                    esp_group.pfs = "disabled"
                else:
                    esp_group.pfs = split_conf[7].strip("'")

            if not len(split_conf) < 10:
                if split_conf[8] == "encryption":
                    esp_group.encryption = split_conf[9].strip("'")

                elif split_conf[8] == "hash":
                    esp_group.hash = split_conf[9].strip("'")

            if not existing_esp_group:
                esp_groups_list.append(esp_group)

        return esp_groups_list

    def get_ike_groups(self, name=None):
        """
        Get IKE Groups configured on v5600 device.
        Sample configs:
        set security vpn ipsec ike-group NetOrc_IKE_PROPOSAL dead-peer-detection action 'restart'
        set security vpn ipsec ike-group NetOrc_IKE_PROPOSAL dead-peer-detection interval '30'
        set security vpn ipsec ike-group NetOrc_IKE_PROPOSAL dead-peer-detection timeout '120'
        set security vpn ipsec ike-group NetOrc_IKE_PROPOSAL lifetime '28800'
        set security vpn ipsec ike-group NetOrc_IKE_PROPOSAL proposal 1 dh-group '5'
        set security vpn ipsec ike-group NetOrc_IKE_PROPOSAL proposal 1 encryption 'aes256'
        set security vpn ipsec ike-group NetOrc_IKE_PROPOSAL proposal 1 hash 'sha1'
        :return: 
        """
        ike_groups_list = list()
        for index, conf in enumerate(self.configs):
            if not conf.startswith("set security vpn ipsec ike-group "):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 8:
                continue

            ike_group_name = split_conf[5].strip()
            if name and name != ike_group_name:
                continue

            existing_ike_group = [ike_group for ike_group in ike_groups_list if ike_group.name == ike_group_name]
            ike_group = existing_ike_group[0] if existing_ike_group else SoftLayerIkeGroup(ike_group_name)

            if split_conf[6] == "lifetime":
                ike_group.lifetime = split_conf[7].strip("'")

            if len(split_conf) > 6 and split_conf[6] == "dead-peer-detection":
                if split_conf[7] == "action":
                    ike_group.dpd_action = split_conf[8].strip("'")

                elif split_conf[7] == "interval":
                    ike_group.dpd_interval = int(split_conf[8].strip("'"))

                elif split_conf[7] == "timeout":
                    ike_group.dpd_timeout = int(split_conf[8].strip("'"))

            if not len(split_conf) < 10:
                if split_conf[8] == "encryption":
                    ike_group.encryption = split_conf[9].strip("'")

                elif split_conf[8] == "dh-group":
                    ike_group.dh_group = split_conf[9].strip("'")

                elif split_conf[8] == "hash":
                    ike_group.hash = split_conf[9].strip("'")

            if not existing_ike_group:
                ike_groups_list.append(ike_group)
        return ike_groups_list

    def get_ipsec(self):
        """
        Get IPSec configured on v5600 device.
        Sample configs:
        set security vpn ipsec site-to-site peer 50.23.185.52 authentication id '169.57.91.205'
        set security vpn ipsec site-to-site peer 50.23.185.52 authentication mode 'pre-shared-secret'
        set security vpn ipsec site-to-site peer 50.23.185.52 authentication pre-shared-secret '********'
        set security vpn ipsec site-to-site peer 50.23.185.52 authentication remote-id '50.23.185.52'
        set security vpn ipsec site-to-site peer 50.23.185.52 connection-type 'respond'
        set security vpn ipsec site-to-site peer 50.23.185.52 default-esp-group 'NETORC_ESP_GROUP'
        set security vpn ipsec site-to-site peer 50.23.185.52 ike-group 'NETORC_IKE_GROUP'
        set security vpn ipsec site-to-site peer 50.23.185.52 local-address '169.57.91.205'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 0 allow-nat-networks 'disable'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 0 allow-public-networks 'disable'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 0 local prefix '172.16.1.245/32'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 0 remote prefix '172.16.2.245/32'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 0 uses 'vfp1'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 1 local prefix '10.130.254.8/30'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 1 remote prefix '10.28.62.128/28'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 2 local prefix '10.131.64.64/26'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 2 remote prefix '10.28.103.64/26'
        :return:
        """
        vpns_list = list()
        for index, conf in enumerate(self.configs):
            if not conf.startswith("set security vpn ipsec site-to-site peer "):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 7:
                continue

            peer_address = split_conf[6].strip()
            existing_vpn = [vpn for vpn in vpns_list if vpn.peer_address == peer_address]
            vpn = existing_vpn[0] if existing_vpn else SoftLayerIpsec(peer_address)

            if len(split_conf) < 10:
                if split_conf[7] == "default-esp-group":
                    vpn.esp_group = self.get_esp_groups(name=split_conf[8].strip("'"))[0]

                elif split_conf[7] == "ike-group":
                    vpn.ike_group = self.get_ike_groups(name=split_conf[8].strip("'"))[0]

            elif len(split_conf) < 11:
                if split_conf[8] == "pre-shared-secret":
                    if not split_conf[9].strip("'").startswith("********"):
                        vpn.pre_shared_secret = split_conf[9].strip("'")

            vpn.tunnels = self.get_ipsec_tunnels(peer_address)

            if not existing_vpn:
                vpns_list.append(vpn)

        return vpns_list

    def get_ipsec_tunnels(self, peer_address):
        """
        Sample Configs:
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 1 local prefix '10.130.254.8/30'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 1 remote prefix '10.28.62.128/28'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 2 local prefix '10.131.64.64/26'
        set security vpn ipsec site-to-site peer 50.23.185.52 tunnel 2 remote prefix '10.28.103.64/26'
        :return:
        """
        ipsec_tunnels_list = list()
        for index, conf in enumerate(self.configs):
            if not conf.startswith("set security vpn ipsec site-to-site peer {} tunnel ".format(peer_address)):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 11:
                continue

            tunnel_no = split_conf[8]
            existing_tunnel = [tunnel for tunnel in ipsec_tunnels_list if tunnel.tunnel_no == tunnel_no]
            ipsec_tunnel = existing_tunnel[0] if existing_tunnel else SoftLayerIpsecTunnel(tunnel_no)
            if split_conf[9] == "local":
                ipsec_tunnel.discovered_local_cidrs = split_conf[11].strip("'")

            elif split_conf[9] == "remote":
                ipsec_tunnel.remote_subnet = split_conf[11].strip("'")

            if not existing_tunnel:
                ipsec_tunnels_list.append(ipsec_tunnel)

        return ipsec_tunnels_list

    def get_firewalls(self, name=None, direction=None, port=None, protocol=None, vif_id=None):
        """
        We can take the reference of firewall applied to VIF to create ACLs.
        set security firewall name TO-SERVICE description 'Bond0.1356 - OUT - External Traffic TO Service'
        set security firewall name TO-SERVICE rule 5 action 'accept'
        set security firewall name TO-SERVICE rule 5 description 'Allow icmp for SoftLayer Server Monitoring'
        set security firewall name TO-SERVICE rule 5 icmp name 'echo-request'
        set security firewall name TO-SERVICE rule 5 protocol 'icmp'
        set security firewall name TO-SERVICE rule 6 action 'accept'
        :return:
        """
        vyatta_firewalls = list()
        for index, conf in enumerate(self.configs):
            if not conf.startswith("set security firewall name ".format(name=name)):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 7:
                continue

            fw_name = split_conf[4].strip()
            if name and name != fw_name:
                continue

            existing_vyatta_firewall = [fw for fw in vyatta_firewalls if fw.name == fw_name]
            vyatta_firewall = existing_vyatta_firewall[0] if existing_vyatta_firewall else SoftLayerFirewall(
                fw_name, direction, vif_id=vif_id)

            if split_conf[5].strip("'") == "rule":
                rule_no = int(split_conf[6].strip())
                if rule_no not in [rule.rule_no for rule in vyatta_firewall.rules]:
                    firewall_rule = self.get_firewall_rule(fw_name, rule_no, direction, port, protocol)
                    if firewall_rule:
                        vyatta_firewall.rules.append(firewall_rule)

            if not existing_vyatta_firewall:
                vyatta_firewalls.append(vyatta_firewall)

        return vyatta_firewalls

    def get_firewall_rule(self, name, rule_no, direction, port=None, protocol=None):
        """
        set security firewall name TO-SERVICE rule 5 action 'accept'
        set security firewall name TO-SERVICE rule 5 description 'Allow icmp for SoftLayer Server Monitoring'
        set security firewall name TO-SERVICE rule 5 icmp name 'echo-request'
        set security firewall name TO-SERVICE rule 5 protocol 'icmp'
        set security firewall name TO-SERVICE rule 6 action 'accept'
        :return:
        """
        fw_rule, ports = None, list()
        for index, conf in enumerate(self.configs):
            if not conf.startswith(
                    "set security firewall name {name} rule {rule_no} ".format(name=name, rule_no=rule_no)):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 9:
                continue

            if not fw_rule:
                fw_rule = SoftLayerFirewallRule(rule_no, direction=direction)

            if split_conf[7] == "protocol":
                if split_conf[8].strip("'") in Vyatta56Analyzer.PROTOCOL_IGNORE_LIST:
                    return

                fw_rule.protocol = split_conf[8].strip("'")

            elif split_conf[7] == "icmp":
                if split_conf[8] and split_conf[8] == "type":
                    fw_rule.type = split_conf[9].strip("'")
                # eg ['set', 'security', 'firewall', 'name', 'icmp-fw', 'rule', '3', 'icmp', 'type', '5', 'code', "'0'"]
                if len(split_conf) > 10 and split_conf[10] == "code":
                    fw_rule.code = split_conf[11].strip("'")

            elif split_conf[7] == "action":
                fw_rule.action = split_conf[8].strip("'")

            elif split_conf[7] == "source":
                if split_conf[8] == "address":
                    address_groups = self.get_address_groups(split_conf[9].strip("'"))
                    if not address_groups:
                        fw_rule.source_addresses.append(split_conf[9].strip("'"))
                    else:
                        fw_rule.source_address_groups.append(address_groups)

                if split_conf[8] == "port":
                    port_groups = self.get_port_groups(split_conf[9].strip("'"))
                    if not port_groups:
                        fw_rule.source_ports.append(split_conf[9].strip("'"))
                    else:
                        fw_rule.source_port_groups.append(port_groups)

            elif split_conf[7] == "destination":
                if split_conf[8] == "address":
                    address_groups = self.get_address_groups(split_conf[9].strip("'"))
                    if not address_groups:
                        fw_rule.destination_addresses.append(split_conf[9].strip("'"))
                    else:
                        fw_rule.destination_address_groups.append(address_groups)
                if split_conf[8] == "port":
                    port_groups = self.get_port_groups(split_conf[9].strip("'"))
                    if not port_groups:
                        fw_rule.destination_ports.append(split_conf[9].strip("'"))
                    else:
                        fw_rule.destination_port_groups.append(port_groups)

            elif split_conf[7] == "description":
                fw_rule.description = " ".join(split_conf[8:])

            if port:
                ports.extend(fw_rule.destination_ports)
                ports.extend(fw_rule.source_ports)
                for port_group in fw_rule.source_port_groups:
                    ports.extend(port_group.ports)

                for port_group in fw_rule.destination_port_groups:
                    ports.extend(port_group.ports)

        if protocol and protocol != fw_rule.protocol:
            return

        if port and port not in ports:
            return

        if fw_rule:
            if protocol and protocol != fw_rule.protocol:
                return

        return fw_rule

    def get_address_groups(self, name):
        """
        Get address resource groups given its name.
        Sample Configs:
        set resources group address-group AG-LAN-SCAN address '10.170.105.94'
        set resources group address-group AG-LAN-SCAN address '10.170.19.237'
        set resources group address-group AG-LAN-SCAN address '10.170.1.236'
        set resources group address-group AG-LAN-SCAN address '10.170.1.200'
        :return:
        """
        address_group = None
        for index, conf in enumerate(self.configs):
            if not conf.startswith(
                    "set resources group address-group {name} ".format(name=name)):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 7:
                continue

            if not address_group:
                address_group = SoftLayerAddressGroup(name)

            if split_conf[5] == "address":
                address_group.addresses.append(split_conf[6].strip("'"))

            elif split_conf[5] == "address-range":
                address_list = calculate_address_range(split_conf[6].strip("'"), split_conf[8].strip("'"))
                if address_list:
                    address_group.addresses.extend(address_list)

        return address_group

    def get_port_groups(self, name):
        """
        Get address port groups given its name.
        Sample Configs:
        set resources group port-group PG-FWD-SANSAY port 'https'
        set resources group port-group PG-FWD-SANSAY port '23200'
        set resources group port-group PG-FWD-SANSAY port '23202'
        set resources group port-group PG-FWD-SANSAY port '22566'
        set resources group port-group PG-FWD-SANSAY port '22568'
        :return:
        """
        port_group = None
        for index, conf in enumerate(self.configs):
            if not conf.startswith(
                    "set resources group port-group {name} ".format(name=name)):
                continue

            split_conf = conf.strip().split()
            if len(split_conf) < 7:
                continue

            if not port_group:
                port_group = SoftLayerPortGroup(name)

            if split_conf[5] == "port":
                port_group.ports.append(split_conf[6].strip("'"))

        return port_group
