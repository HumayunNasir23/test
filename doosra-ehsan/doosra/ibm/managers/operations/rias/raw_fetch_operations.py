from flask import current_app
from requests.exceptions import ConnectionError, ReadTimeout, RequestException
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.operations.rias.consts import GENERATION, VERSION
from doosra.ibm.managers.operations.rias.rias_patterns import *
from doosra.models import IBMCredentials


class RawFetchOperations(object):
    def __init__(self, cloud, region, base_url, session, iam_ops, resource_ops, k8s_base_url=None, session_k8s=None):
        self.cloud = cloud
        self.region = region
        self.base_url = base_url
        self.k8s_base_url = k8s_base_url
        self.session = session
        self.session_k8s = session_k8s
        self.iam_ops = iam_ops
        self.resource_ops = resource_ops

    def get_all_networks_acls(self, name=None):
        """
        Fetch all network ACLs in the region.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_ACLS_PATTERN))
        acls = response.get("network_acls")
        if not acls:
            return []
        return [
            {
                "name": acl["name"],
                "id": acl["id"],
                "vpc_id": acl["vpc"]["id"],
                "rules": [
                    {
                        "id": rule["id"],
                        "name": rule["name"],
                        "action": rule["action"],
                        "destination": rule.get("destination"),
                        "source": rule.get("source"),
                        "direction": rule["direction"],
                        "protocol": rule["protocol"],
                        "port_max": rule.get("destination_port_max"),
                        "port_min": rule.get("destination_port_min"),
                        "source_port_max": rule.get("source_port_max"),
                        "source_port_min": rule.get("source_port_min"),
                        "code": rule.get("code"),
                        "type": rule.get("type"),
                    }
                    for rule in acl.get("rules", [])
                ],
            }
            for acl in acls
        ]

    def get_all_floating_ips(self, name=None):
        """
        Fetch all floating ips in the region.
        :return:
        """
        floating_ip_list = list()
        response = self.execute(self.format_api_url(LIST_FLOATING_IPS_PATTERN))
        floating_ips = response.get("floating_ips", [])
        for floating_ip in floating_ips:
            if name and name != floating_ip["name"]:
                continue

            floating_ip_list.append({
                "id": floating_ip["id"],
                "name": floating_ip["name"],
                "zone": floating_ip["zone"]["name"],
                "address": floating_ip["address"],
                "status": floating_ip["status"]
            })

        return floating_ip_list

    def get_all_ssh_keys(self, name=None):
        """
        Fetch all ssh keys in the region.
        :return:
        """
        ssh_key_list = list()
        response = self.execute(self.format_api_url(LIST_SSH_KEYS_PATTERN))
        ssh_keys = response.get("keys", [])
        for ssh_key in ssh_keys:
            if name and name != ssh_key["name"]:
                continue

            ssh_key_list.append({
                "name": ssh_key["name"],
                "type": ssh_key["type"],
                "public_key": ssh_key["public_key"],
                "finger_print": ssh_key["fingerprint"],
                "resource_id": ssh_key["id"],
                "resource_group_id": ssh_key["resource_group"]["id"],
            })
        return ssh_key_list

    def get_all_ike_policies(self, name=None):
        """
        Fetch all ike policies in the region.
        :return:
        """
        ike_policies_list = list()
        response = self.execute(self.format_api_url(LIST_IKE_POLICIES))
        ike_policies = response.get("ike_policies", [])
        for ike_policy in ike_policies:
            if name and name != ike_policy["name"]:
                continue

            ike_policies_list.append({
                "name": ike_policy["name"],
                "key_lifetime": ike_policy["key_lifetime"],
                "ike_version": ike_policy["ike_version"],
                "authentication_algorithm": ike_policy["authentication_algorithm"],
                "encryption_algorithm": ike_policy["encryption_algorithm"],
                "dh_group": ike_policy["dh_group"],
                "id": ike_policy["id"],
                "resource_group_id": ike_policy["resource_group"]["id"],
            })

        return ike_policies_list

    def get_all_ipsec_policies(self, name=None):
        """
        Fetch all ipsec policies in the region.
        :return:
        """
        ipsec_policies_list = list()
        response = self.execute(self.format_api_url(LIST_IPSEC_POLICIES))
        ipsec_policies = response.get("ipsec_policies", [])
        for ipsec_policy in ipsec_policies:
            if name and name != ipsec_policy["name"]:
                continue

            ipsec_policies_list.append({
                "name": ipsec_policy["name"],
                "key_lifetime": ipsec_policy["key_lifetime"],
                "authentication_algorithm": ipsec_policy["authentication_algorithm"],
                "encryption_algorithm": ipsec_policy["encryption_algorithm"],
                "pfs_dh_group": ipsec_policy["pfs"],
                "id": ipsec_policy["id"],
                "resource_group_id": ipsec_policy["resource_group"]["id"],
            })

        return ipsec_policies_list

    def get_all_volume_profiles(self, name=None):
        """
        Fetch all volume profiles available in the region.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_VOLUME_PROFILES_PATTERN))
        volume_profiles = response.get("profiles")
        if not volume_profiles:
            return []
        return [
            {
                "name": volume_profile["name"],
                "family": volume_profile.get("family"),
                "generation": volume_profile.get("generation"),
            }
            for volume_profile in volume_profiles
        ]

    def get_all_instance_profiles(self, name=None):
        """
        Fetch all instance profiles available in the region.
        :return:
        """
        instance_profiles_list = list()
        response = self.execute(self.format_api_url(LIST_INSTANCE_PROFILES_PATTERN))
        instance_profiles = response.get("profiles", [])
        for instance_profile in instance_profiles:
            if name and name != instance_profile["name"]:
                continue

            instance_profiles_list.append({"name": instance_profile["name"], "family": instance_profile.get("family"),
                                           "architecture": instance_profile["vcpu_architecture"]["value"]})

        return instance_profiles_list

    def get_all_images(self, name=None, visibility=None):
        """
        Fetch all images available in the region.
        :return:
        """
        images_list = list()
        response = self.execute(self.format_api_url(LIST_IMAGES_PATTERN))
        images = response.get("images", [])
        for image in images:
            if not ((name and name != image["name"]) or (visibility and visibility != image["visibility"])):
                images_list.append({
                    "name": image["name"],
                    "visibility": image["visibility"],
                    "id": image["id"],
                    "size": image["file"].get("size"),
                    "operating_system_name": image["operating_system"]["name"],
                    "status":image["status"]
                })
        return images_list

    def get_all_operating_systems(self, name=None):
        """
        Fetch all operating systems available in the region.
        :return:
        """
        operating_system_list = list()
        response = self.execute(self.format_api_url(LIST_OPERATING_SYSTEMS_PATTERN))
        operating_systems = response.get("operating_systems", [])
        for operating_system in operating_systems:
            if name and name != operating_system["name"]:
                continue

            operating_system_list.append({
                "name": operating_system["name"],
                "architecture": operating_system["architecture"],
                "family": operating_system["family"],
                "vendor": operating_system["vendor"],
                "version": operating_system["version"],
            })

        return operating_system_list

    def get_all_volumes(self, name=None):
        """
        Fetch all volumes available in the region.
        :return:
        """
        volumes_list = list()
        response = self.execute(self.format_api_url(LIST_VOLUMES_PATTERN))
        volumes = response.get("volumes", [])
        for volume in volumes:
            if name and name != volume["name"]:
                continue

            if volume["status"] != "available":
                continue

            volumes_list.append({
                "name": volume["name"],
                "capacity": volume["capacity"],
                "zone": volume["zone"]["name"],
                "iops": volume["iops"],
                "encryption": volume["encryption"],
                "id": volume["id"],
                "profile_name": volume["profile"]["name"],
                "volume_attachments_info": [{
                    "name": volume_attachments["name"],
                    "id": volume_attachments["id"],
                    "type": volume_attachments["type"],
                    "instance_id": volume_attachments["instance"]["id"]
                } for volume_attachments in volume["volume_attachments"]]
            })

        return volumes_list

    def get_all_security_groups(self, name=None):
        """
        Fetch all security groups available in the region.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_SECURITY_GROUPS_PATTERN))
        security_groups = response.get("security_groups")
        if not security_groups:
            return []
        return [
            {
                "name": security_group["name"],
                "id": security_group["id"],
                "resource_group_id": security_group["resource_group"]["id"],
                "vpc_id": security_group["vpc"]["id"],
                "rules": [
                    {
                        "id": rule["id"],
                        "direction": rule["direction"],
                        "protocol": rule.get("protocol"),
                        "code": rule.get("code"),
                        "type": rule.get("type"),
                        "port_min": rule.get("port_min"),
                        "port_max": rule.get("port_max"),
                        "address": rule.get("address"),
                        "cidr_block": rule.get("cidr_block"),
                    }
                    for rule in security_group.get("rules", [])
                ],
            }
            for security_group in security_groups
        ]

    def get_all_vpcs(self, name=None):
        """
        Fetch all vpcs available in the region.
        :return:
        """
        vpcs_list = list()
        response = self.execute(self.format_api_url(LIST_VPCS_PATTERN))
        vpcs = response.get("vpcs", [])
        for vpc in vpcs:
            if name and name != vpc["name"]:
                continue

            vpcs_list.append(
                {
                    "name": vpc["name"],
                    "classic_access": vpc["classic_access"],
                    "id": vpc["id"],
                    "crn": vpc["crn"],
                    "resource_group_id": vpc["resource_group"]["id"],
                    "default_network_acl_id": vpc["default_network_acl"]["id"],
                    "default_security_group_id": vpc["default_security_group"]["id"],
                    "status": vpc["status"]
                }
            )
        return vpcs_list

    def get_all_subnets(self, name=None):
        """
        Fetch all subnets available in the region.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_SUBNETS_PATTERN))
        subnets = response.get("subnets")
        if not subnets:
            return []
        return [
            {
                "name": subnet["name"],
                "zone": subnet["zone"]["name"],
                "ipv4_cidr_block": subnet["ipv4_cidr_block"],
                "id": subnet["id"],
                "network_acl_id": subnet["network_acl"].get("id"),
                "vpc_id": subnet["vpc"]["id"],
                "public_gateway_id": subnet["public_gateway"]["id"]
                if subnet.get("public_gateway")
                else None,
                "status": subnet['status']
            }
            for subnet in subnets
        ]

    def get_all_public_gateways(self):
        """
        Fetch all public gateways available in the region.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_PUBLIC_GATEWAYS_PATTERN))
        public_gateways = response.get("public_gateways")
        if not public_gateways:
            return []
        return [
            {
                "name": public_gateway["name"],
                "zone": public_gateway["zone"]["name"],
                "id": public_gateway["id"],
                "vpc_id": public_gateway["vpc"]["id"],
                "floating_ip": {
                    "id": public_gateway["floating_ip"]["id"],
                    "name": public_gateway["floating_ip"]["name"],
                    "address": public_gateway["floating_ip"]["address"],
                },
                "status": public_gateway["status"]
            }
            for public_gateway in public_gateways
        ]

    def get_all_address_prefixes(self, vpc_id, name=None):
        """
        Fetch all address prefixes available in the region.
        :return:
        """
        response = self.execute(
            self.format_api_url(LIST_ADDRESS_PREFIXES_PATTERN, vpc_id=vpc_id)
        )
        address_prefixes = response.get("address_prefixes")
        if not address_prefixes:
            return []
        return [
            {
                "name": address_prefix["name"],
                "zone": address_prefix["zone"]["name"],
                "address": address_prefix["cidr"],
                "id": address_prefix["id"],
                "is_default": address_prefix["is_default"],
            }
            for address_prefix in address_prefixes
        ]

    def get_all_vpn_gateways(self, name=None, vpc_name=None):
        """
        Fetch all VPN gateways available in the region.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_VPN_GATEWAYS_PATTERN))
        vpn_gateways = response.get("vpn_gateways")
        if not vpn_gateways:
            return []
        return [
            {
                "name": vpn_gateway["name"],
                "id": vpn_gateway["id"],
                "public_ip": vpn_gateway["public_ip"]["address"] if vpn_gateway.get("public_ip") else "",
                "created_at": vpn_gateway["created_at"],
                "gateway_status": vpn_gateway["status"],
                "subnet_id": vpn_gateway["subnet"]["id"],
                "resource_group_id": vpn_gateway["resource_group"]["id"],
                "status":vpn_gateway["status"]
            }
            for vpn_gateway in vpn_gateways
        ]

    def get_all_vpn_connections(self, vpn_gateway_id, name=None):
        """
        Fetch all Connections specific to a VPN gateway available in the region.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                LIST_VPN_GATEWAY_CONNECTIONS_PATTERN, vpn_gateway_id=vpn_gateway_id
            )
        )
        vpn_connections = response.get("connections")
        if not vpn_connections:
            return []
        return [
            {
                "name": connection["name"],
                "peer_address": connection["peer_address"],
                "psk": connection["psk"],
                "local_cidrs": json.dumps(connection["local_cidrs"]) if connection.get("local_cidrs") else [],
                "peer_cidrs": json.dumps(connection["peer_cidrs"]) if connection.get("peer_cidrs") else [],
                "dpd_interval": connection["dead_peer_detection"]["interval"],
                "dpd_timeout": connection["dead_peer_detection"]["timeout"],
                "dpd_action": connection["dead_peer_detection"]["action"],
                "id": connection["id"],
                "ike_policy_id": connection["ike_policy"]["id"] if connection.get("ike_policy") else None,
                "ipsec_policy_id": connection["ipsec_policy"]["id"] if connection.get("ipsec_policy") else None,
                "authentication_mode": connection["authentication_mode"],
                "created_at": connection["created_at"],
                "vpn_status": connection["status"],
                "route_mode": connection.get("route_mode"),
            }
            for connection in vpn_connections
        ]

    def get_all_load_balancers(self, name=None):
        """
        Fetch all load balancers available in the region.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_LOAD_BALANCERS_PATTERN))
        load_balancers = response.get("load_balancers")
        if not load_balancers:
            return []
        return [
            {
                "name": load_balancer["name"],
                "is_public": load_balancer["is_public"],
                "host_name": load_balancer["hostname"],
                "provisioning_status": load_balancer["provisioning_status"],
                "id": load_balancer["id"],
                "listeners_id": [
                    listener["id"] for listener in load_balancer["listeners"]
                ],
                "pools_id": [pool["id"] for pool in load_balancer["pools"]],
                "subnets": [subnet["id"] for subnet in load_balancer["subnets"]],
                "resource_group_id": load_balancer["resource_group"]["id"],
                "private_ips": [
                    private_ip["address"] for private_ip in load_balancer["private_ips"]
                ]
                if load_balancer.get("private_ips")
                else None,
                "public_ips": [
                    public_ips["address"] for public_ips in load_balancer["public_ips"]
                ]
                if load_balancer.get("public_ips")
                else None,
            }
            for load_balancer in load_balancers
        ]

    def get_all_listeners(self, load_balancer_id):
        """
        Fetch all listeners specific to a load balancer available in the region.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                LIST_LOAD_BALANCERS_LISTENERS_PATTERN, load_balancer_id=load_balancer_id
            )
        )
        listeners = response.get("listeners")
        if not listeners:
            return []
        return [
            {
                "port": listener["port"],
                "protocol": listener["protocol"],
                "limit": listener.get("limit"),
                "crn": listener.get("crn"),
                "id": listener["id"],
                "default_pool_name": listener["default_pool"]["name"]
                if listener.get("default_pool")
                else None,
            }
            for listener in listeners
        ]

    def get_all_pools(self, load_balancer_id):
        """
        Fetch all pools specific to a load balancer available in the region.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                LIST_LOAD_BALANCERS_POOLS_PATTERN, load_balancer_id=load_balancer_id
            )
        )
        pools = response.get("pools")
        if not pools:
            return []
        return [
            {
                "name": pool["name"],
                "algorithm": pool["algorithm"],
                "protocol": pool["protocol"],
                "id": pool["id"],
                "session_persistence": pool["session_persistence"]["type"]
                if pool.get("session_persistence")
                else None,
                "health_monitor": {
                    "delay": pool["health_monitor"].get("delay"),
                    "max_retries": pool["health_monitor"].get("max_retries"),
                    "timeout": pool["health_monitor"].get("timeout"),
                    "type": pool["health_monitor"].get("type"),
                    "url_path": pool["health_monitor"].get("url_path"),
                    "port": pool["health_monitor"].get("port"),
                }
                if pool.get("health_monitor")
                else None,
            }
            for pool in pools
        ]

    def get_all_instances(self, name=None):
        """
        Fetch all instances available in the region.
        :return:
        """
        instances_list = list()
        response = self.execute(self.format_api_url(LIST_INSTANCES_PATTERN))
        instances = response.get("instances", [])
        for instance in instances:
            if name and name != instance["name"]:
                continue

            instances_list.append({
                "name": instance["name"],
                "zone": instance["zone"]["name"],
                "instance_status": instance["status"],
                "id": instance["id"],
                "image_id": instance["image"]["id"] if instance.get("image") else None,
                "profile_name": instance["profile"]["name"],
                "vpc_id": instance["vpc"]["id"],
                "resource_group_id": instance["resource_group"]["id"],
                "boot_volume_attachment": {
                    "name": instance["boot_volume_attachment"]["name"],
                    "id": instance["boot_volume_attachment"]["id"],
                    "boot_volume_name": instance["boot_volume_attachment"]["volume"][
                        "name"
                    ],
                }
                if instance.get("boot_volume_attachment")
                else None,
                "volume_attachments": [
                    {
                        "name": volume["name"],
                        "id": volume["id"],
                        "volume_name": volume["volume"]["name"],
                    }
                    for volume in instance["volume_attachments"]
                ]
                if instance.get("volume_attachments")
                else None,
                "ibm_primary_network_interface_name": instance[
                    "primary_network_interface"
                ]["name"]
                if instance.get("primary_network_interface")
                else None,
                "status":instance["status"]
            })

        return instances_list

    def get_instance_network_interfaces(self, instance_id):
        """
        This request lists all network interfaces associated with a instance.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_INSTANCE_NETWORK_INTERFACES_PATTERN, instance_id=instance_id))
        instance_network_interface = response.get("network_interfaces")
        if not instance_network_interface:
            return []
        return [{
            "name": interface["name"],
            "id": interface["id"],
            "subnet_id": interface["subnet"]["id"],
            "security_groups": [sec_grp["id"] for sec_grp in interface["security_groups"]],
            "primary_ipv4_address": interface["primary_ipv4_address"]
        } for interface in instance_network_interface]

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
        if not response.get("floating_ips"):
            return None, None
        floating_ip = response["floating_ips"][0]
        return floating_ip["id"], floating_ip["name"]

    def get_instance_ssh_keys(self, instance_id):
        """
        Fetch all instance ssh keys.
        :return:
        """
        response = self.execute(
            self.format_api_url(GET_INSTANCE_SSH_KEYS_PATTERN, instance_id=instance_id)
        )
        ssh_keys = response.get("keys")
        if not response:
            return []
        return [ssh_key["id"] for ssh_key in ssh_keys]

    def get_all_pool_members(self, load_balancer_id, pool_id):
        """
        Fetch all pool members specific to a load balancer available in the region.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                LIST_POOL_MEMBERS_PATTERN,
                load_balancer_id=load_balancer_id,
                pool_id=pool_id,
            )
        )
        members = response.get("members")
        if not members:
            return []
        return [
            {
                "port": member["port"],
                "weight": member["weight"],
                "id": member["id"],
                "status": member["provisioning_status"],
                "member_target_address": member["target"]["address"]
                if member.get("target")
                else None,
            }
            for member in members
        ]
    
    def get_all_k8s_clusters(self):
        """
        Fetch all K8s Clusters.
        :return:
        """
        k8s_cluster_list = list()
        k8s_clusters = self.execute_(self.format_api_url(LIST_K8S_CLUSTERS_PATTERN))
        if not k8s_clusters:
            return k8s_cluster_list

        for k8s_cluster in k8s_clusters:
            cluster = {
                "name": k8s_cluster['name'],
                "disable_public_service_endpoint": False,
                "kube_version": k8s_cluster['masterKubeVersion'],
                "pod_subnet": k8s_cluster['podSubnet'],
                "provider": k8s_cluster['provider'],
                "type": k8s_cluster['type'],
                "service_subnet": k8s_cluster['serviceSubnet'],
                "worker_count": k8s_cluster['workerCount'],
                "status": k8s_cluster['status'],
                "state": k8s_cluster['state'],
                "cloud_id": self.cloud.id,
                "resource_id": k8s_cluster['id'],
                "resource_group_id": k8s_cluster['resourceGroup'],
                "region": k8s_cluster['region'],
                "worker_pools": []
            }
            k8s_cluster_list.append(cluster)
        return k8s_cluster_list

    def get_all_k8s_cluster_worker_pool(self, cluster_id):
        """
        Fetch all K8s Workerpools of a Cluster.
        :return:
        """
        worker_pool_list = list()
        k8s_cluster_worker_pools = self.execute_(self.format_api_url(GET_K8S_CLUSTERS_WORKER_POOL,
                                                                     cluster=cluster_id))
        if not k8s_cluster_worker_pools:
            return worker_pool_list

        for k8s_workerpool in k8s_cluster_worker_pools:
            workerpool = {
                "name": k8s_workerpool['poolName'],
                "flavor": k8s_workerpool['flavor'],
                "worker_count": k8s_workerpool['workerCount'],
                "resource_id": k8s_workerpool['id'],
                "vpc_resource_id": k8s_workerpool['vpcID'],
                "cluster_id": cluster_id,
                "zones": []
            }
            for k8s_worker_zone in k8s_workerpool['zones']:
                zone = {
                    "name": k8s_worker_zone['id'],
                    "subnets": []
                }
                for zone_subnet in k8s_worker_zone['subnets']:
                    subnet = {
                        "subnet_id": zone_subnet['id']
                    }
                    zone["subnets"].append(subnet)
                workerpool["zones"].append(zone)
            worker_pool_list.append(workerpool)
        return worker_pool_list

    @staticmethod
    def format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the unformatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def execute(self, request, data=None):
        request_url = request[1].format(
            base_url=self.base_url, version=VERSION, generation=GENERATION
        )
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)
        try:
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(
                    IBMCredentials(self.iam_ops.authenticate_cloud_account())
                )
            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.debug("{0} : {1}".format(request[0], request_url))
            response = self.session.request(
                request[0], request_url, data=data, timeout=50, headers=headers
            )
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request_url)
        else:
            if response.status_code in [401, 403]:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code in [400, 408, 500]:
                raise IBMExecuteError(response)
            elif response.status_code == 409:
                raise IBMInvalidRequestError(response)
            elif response.status_code not in [200, 201, 204, 404]:
                raise IBMExecuteError(response)

            resp = response.json()
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

    def execute_(self, request, data=None):
        request_url = request[1].format(
            k8s_base_url=self.k8s_base_url
        )
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)
        try:
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(
                    IBMCredentials(self.iam_ops.authenticate_cloud_account())
                )
            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.debug("{0} : {1}".format(request[0], request_url))
            response = self.session_k8s.request(
                request[0], request_url, data=data, timeout=50, headers=headers
            )
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request_url)
        else:
            if response.status_code in [401, 403]:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code in [400, 408, 500]:
                raise IBMExecuteError(response)
            elif response.status_code == 409:
                raise IBMInvalidRequestError(response)
            elif response.status_code not in [200, 201, 204, 404]:
                raise IBMExecuteError(response)

            resp = response.json()
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
