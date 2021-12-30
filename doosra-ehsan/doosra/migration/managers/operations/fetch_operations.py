import logging
from typing import List, Dict

from SoftLayer import BaseClient
from SoftLayer.exceptions import SoftLayerAPIError
from SoftLayer.managers import (
    DedicatedHostManager,
    LoadBalancerManager,
    FirewallManager,
    NetworkManager,
    ImageManager,
    SshKeyManager,
    SSLManager,
    VSManager,
)
from dateutil import parser
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from doosra.common.clients.ibm_clients.kubernetes.kubernetes import ClassicKubernetesClient
from doosra.common.clients.ibm_clients.kubernetes.utils import K8s
from doosra.common.consts import classical_vpc_image_dictionary, CREATION_PENDING
from doosra.ibm.managers.exceptions import IBMInvalidRequestError, IBMAuthError, IBMConnectError, IBMExecuteError
from doosra.migration.common.utils import get_ibm_instance_profile
from doosra.migration.managers.consts import *
from doosra.migration.managers.exceptions import SLAuthError, SLExecuteError, SLRateLimitExceededError
from doosra.migration.managers.operations.consts import BACK_OFF_FACTOR, INVALID_API_KEY_CODE, MAX_INTERVAL, RETRY, \
    SL_RATE_LIMIT_FAULT_CODE
from doosra.migration.models import SoftLayerSubnet
from doosra.migration.models.softlayer_models import (
    SoftLayerListener,
    SoftLayerLoadBalancer,
    SoftLayerInstance,
    SoftLayerSshKey,
    SoftLayerImage,
    SoftLayerInstanceProfile,
    SoftLayerBackendPool,
    SoftLayerPoolHealthMonitor,
    SoftLayerPoolMember,
    SoftLayerNetworkInterface,
    SoftLayerSecurityGroup,
    SoftLayerSecurityGroupRule,
    SoftLayerVolume,
    SoftLayerDedicatedHost
)
from doosra.migration.models.utils import get_auto_scale_group, list_network_attached_storages
from doosra.models.ibm.kubernetes_models import KubernetesCluster, KubernetesClusterWorkerPool, \
    KubernetesClusterWorkerPoolZone

LOGGER = logging.getLogger(__name__)


class FetchOperations:
    client: BaseClient
    dedicated_host_manager: DedicatedHostManager
    load_balancer_manager: LoadBalancerManager
    firewall_manager: FirewallManager
    network_manager: NetworkManager
    image_manager: ImageManager
    ssh_manager: SshKeyManager
    ssl_manager: SSLManager
    vs_manager: VSManager

    def __init__(self, client, username):
        self.client = client
        self.username = username
        self.retry = self.requests_retry()

    def requests_retry(self):
        self.retry = Retrying(
            stop=stop_after_attempt(RETRY),
            retry=retry_if_exception_type(SLRateLimitExceededError),
            wait=wait_random_exponential(multiplier=BACK_OFF_FACTOR, max=MAX_INTERVAL),
            reraise=True)
        return self.retry

    def authenticate_sl_account(self):
        """
        Authenticate SL account with provided credentials
        :return:
        """
        try:
            return self.retry.call(self.client.call, "Account", "getObject")
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def list_private_subnets(self, vlan_no=None, network_identifier=None) -> list:
        """List all the private Subnetworks associated with an Account."""

        subnets_list = list()
        try:
            self.network_manager = NetworkManager(self.client)
            vlans = self.retry.call(self.network_manager.list_vlans,
                                    filter={"networkVlans": {"subnets": {"addressSpace": {"operation": "PRIVATE"}}}},
                                    mask="mask{subnets}".format(subnets=SUBNET_MASK))

            for vlan in vlans:
                if vlan_no and vlan_no != vlan.get("vlanNumber"):
                    continue

                vlan_name = "{}-{{}}".format(vlan.get("name") or "subnet-{}".format(vlan.get("vlanNumber")))
                count = 1
                for subnet in vlan.get("subnets", []):
                    sl_subnet = SoftLayerSubnet(
                        name=vlan_name.format(count), vif_id=vlan.get("vlanNumber"),
                        address="{}/{}".format(subnet.get("gateway"), subnet.get("cidr")),
                        network_id=subnet["networkIdentifier"])
                    count = count + 1
                    if not (network_identifier and network_identifier != sl_subnet.network_id):
                        subnets_list.append(sl_subnet)

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

        return subnets_list

    def get_instance_by_id(self, instance_id):
        """
        Get a softlayer instance, with provided ID
        :return:
        """
        try:
            self.vs_manager = VSManager(self.client)
            instances = self.retry.call(self.vs_manager.get_instance, instance_id=instance_id)

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
        else:
            return instances

    def wait_instance_for_ready(self, instance_id, limit=10):
        try:
            self.vs_manager = VSManager(self.client)
            return self.vs_manager.wait_for_ready(instance_id, limit=limit)

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                return False
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def get_image_by_name(self, image_name, create_date=None):
        """
        Get image on the basis of image name.
        :param image_name: Name of the image.
        :param create_date: Creation Date of image
        :return: Return the filtered image on the basis of above params.
        """
        try:
            image_manager = ImageManager(self.client)
            images = self.retry.call(image_manager.list_private_images, name=image_name)
            if not images:
                return
            if not create_date or len(images) == 1:
                return images[0]
            else:
                try:
                    time_list = [
                        abs((parser.parse(image["createDate"]) - parser.parse(create_date)).total_seconds()) for
                        image in images]
                    minimum_index = time_list.index(min(time_list))
                    return images[minimum_index]
                except (parser.ParserError, KeyError, IndexError):
                    return images[0]

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def get_image_by_id(self, image_id):
        """
        Get image on the basis of image id.
        :param image_id: Classical ID of the image.
        :return: Return the filtered image on the basis of above params.
        """
        try:
            image_manager = ImageManager(self.client)
            image = self.retry.call(image_manager.get_image, image_id=image_id)
            if image:
                return image

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def __parse_to_softlayer(self, vs_instance, subnets=None, address=None, ssh_keys_required=True,
                             security_groups_required=True):
        if not (vs_instance["status"].get("keyName") == "ACTIVE" and vs_instance.get("operatingSystem")):
            return

        sl_instance = SoftLayerInstance.from_softlayer_json(instance_json=vs_instance)
        sl_instance.auto_scale_group = get_auto_scale_group(vs_instance)
        sl_instance.network_attached_storages = list_network_attached_storages(
            vs_instance.get('allowedNetworkStorage'))
        instance_profile, family = get_ibm_instance_profile(vs_instance["maxCpu"], vs_instance["maxMemory"])
        sl_instance.instance_profile = SoftLayerInstanceProfile(name=instance_profile, family=family)

        os = vs_instance["operatingSystem"]["softwareLicense"]["softwareDescription"]
        sl_instance.image = SoftLayerImage.from_softlayer_json(operating_system=os)

        if ssh_keys_required:
            sl_instance.ssh_keys.extend([
                SoftLayerSshKey.from_softlayer_json(ssh_key) for ssh_key in vs_instance.get("sshKeys", [])
            ])

        for volume in vs_instance.get("blockDevices", []):
            if not volume.get("diskImage"):
                continue

            SWAP = "SWAP" in volume["diskImage"].get("description", "")
            MB = "MB" == volume["diskImage"].get("units")
            CLOUD_INIT_DISK = 64 == volume["diskImage"].get("capacity")
            if not ((CLOUD_INIT_DISK and MB) or SWAP):
                volume_name = f"{sl_instance.name}-{volume['diskImage'].get('name')}"
                sl_instance.volumes.append(
                    SoftLayerVolume.from_softlayer_json(name=volume_name, volume_json=volume))

        for network in vs_instance.get("networkComponents", []):
            if not network.get("primarySubnet"):
                continue

            interface_name = "{name}{port}".format(name=network.get("name"), port=network.get("port"))
            sl_interface = SoftLayerNetworkInterface(interface_name, network.get("primaryIpAddress"))

            if interface_name == "eth0":
                sl_interface.is_primary = True
            if network["primarySubnet"].get("addressSpace") == "PUBLIC":
                sl_interface.is_public_interface = True

            if subnets:
                attached_subnet = [
                    subnet for subnet in subnets
                    if subnet.vif_id == network["networkVlan"].get("vlanNumber")
                       and subnet.network_id == network["primarySubnet"].get("networkIdentifier")]
            else:
                attached_subnet = self.list_private_subnets(
                    vlan_no=network["networkVlan"].get("vlanNumber"),
                    network_identifier=network["primarySubnet"].get("networkIdentifier"))

            if attached_subnet:
                sl_interface.subnet = attached_subnet[0]
            if security_groups_required:
                for security_group in network.get("securityGroupBindings", []):
                    if not security_group.get("securityGroup"):
                        continue

                    if not security_group["securityGroup"].get("name"):
                        continue

                    sl_security_group = SoftLayerSecurityGroup(name=security_group["securityGroup"]["name"])
                    for rule in security_group["securityGroup"].get("rules", []):
                        if rule["ethertype"] == "IPv6":
                            continue

                        sl_security_group_rule = SoftLayerSecurityGroupRule(
                            direction=rule["direction"], protocol=rule.get("protocol", "all"),
                            port_max=rule.get("portRangeMax"), port_min=rule.get("portRangeMin"),
                            address=network["primaryIpAddress"])

                        sl_security_group.rules.append(sl_security_group_rule)
                    sl_interface.security_groups.append(sl_security_group)
                sl_instance.network_interfaces.append(sl_interface)
            else:
                sl_instance.network_interfaces.append(sl_interface)
        if not (address and address not in [interface.private_ip
                                            for interface in sl_instance.network_interfaces]):
            return sl_instance

    def get_instance_details(self, instance_id, ssh_keys_required=False, security_groups_required=False):
        details = {'ssh_keys_required': ssh_keys_required, 'security_groups_required': security_groups_required}
        self.vs_manager = VSManager(self.client)
        try:
            instance = self.retry.call(self.vs_manager.get_instance, mask=VIRTUAL_SERVER_MASK, instance_id=instance_id)
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
        else:
            instance = self.__parse_to_softlayer(instance, **details)
            return instance

    def list_virtual_servers(self, address=None, subnets=None, ssh_keys_required=True,
                             security_groups_required=True) -> List:
        """Retrieve a list of all virtual servers on the Account."""
        details = {'address': address, 'subnets': subnets, 'ssh_keys_required': ssh_keys_required,
                   'security_groups_required': security_groups_required}
        instances_list = []
        self.vs_manager = VSManager(self.client)
        try:
            instances = self.retry.call(self.vs_manager.list_instances, mask=VIRTUAL_SERVER_MASK)
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
        else:
            for instance in instances:
                instance_obj = self.__parse_to_softlayer(instance, **details)
                if instance_obj:
                    instances_list.append(instance_obj)
            return instances_list

    def list_load_balancers(self, vs_instances=None) -> list:
        """Returns a list of IBM Cloud Loadbalancers"""
        load_balancers_list = list()
        try:
            self.load_balancer_manager = LoadBalancerManager(self.client)
            load_balancers = self.retry.call(self.load_balancer_manager.get_lbaas, mask=LOAD_BALANCER_MASK)
            for lb in load_balancers:
                pools_list, subnets_list = list(), list()
                sl_load_balancer = SoftLayerLoadBalancer(lb["name"], lb["isPublic"], lb["address"])
                for listener in lb.get("listeners", []):
                    sl_listener = SoftLayerListener(
                        protocol=listener.get("protocol"), port=listener.get("protocolPort"),
                        connection_limit=listener.get("connectionLimit"))

                    if listener.get("defaultPool"):
                        sl_pool = SoftLayerBackendPool(
                            port=listener["defaultPool"].get("protocolPort"),
                            protocol=listener["defaultPool"].get("protocol"),
                            algorithm=listener["defaultPool"].get("loadBalancingAlgorithm"))

                        if listener["defaultPool"].get("sessionAffinity"):
                            sl_pool.session_persistence = listener["defaultPool"]["sessionAffinity"].get("type")
                        if listener["defaultPool"].get("healthMonitor"):
                            sl_health_monitor = SoftLayerPoolHealthMonitor(
                                listener["defaultPool"]["healthMonitor"].get("maxRetries"),
                                listener["defaultPool"]["healthMonitor"].get("timeout"),
                                listener["defaultPool"]["healthMonitor"].get("monitorType"),
                                listener["defaultPool"]["healthMonitor"].get("urlPath"),
                                listener["defaultPool"]["healthMonitor"].get("interval"))
                            sl_pool.health_monitor = sl_health_monitor

                        for member in listener["defaultPool"].get("members", []):
                            sl_pool_mem = SoftLayerPoolMember(
                                weight=member.get("weight"), port=listener.get("protocolPort"),
                                ip=member.get("address"))

                            if not vs_instances:
                                instance = self.list_virtual_servers(address=member.get("address"))
                            else:
                                instance = [instance for instance in vs_instances if member.get("address") in
                                            [interf.private_ip for interf in instance.network_interfaces]]

                            if not instance:
                                continue

                            sl_pool_mem.instance = instance[0]
                            for network_interface in sl_pool_mem.instance.network_interfaces:
                                if not network_interface.subnet:
                                    continue

                                if network_interface.subnet.name not in [subnet.name for subnet in subnets_list]:
                                    subnets_list.append(network_interface.subnet)

                            sl_pool.pool_members.append(sl_pool_mem)
                        sl_listener.backend_pool = sl_pool
                        pools_list.append(sl_pool)
                    sl_load_balancer.listeners.append(sl_listener)

                sl_load_balancer.pools = pools_list
                sl_load_balancer.subnets = subnets_list
                load_balancers_list.append(sl_load_balancer)

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
        else:
            return load_balancers_list

    def list_security_groups(self) -> list:
        """List all the Security Groups within an Account."""
        sl_security_groups_list = list()
        try:
            security_groups = self.retry.call(
                NetworkManager(self.client).list_securitygroups, mask="mask{mask}".format(
                    mask="[networkComponentBindings, rules]"))
            for security_group in security_groups:
                sl_security_group = SoftLayerSecurityGroup(name=security_group["name"])
                for rule in security_group.get("rules", []):
                    if rule["ethertype"] == "IPv6":
                        continue

                    sl_security_group_rule = SoftLayerSecurityGroupRule(
                        direction=rule["direction"], protocol=rule.get("protocol", "all"),
                        port_max=rule.get("portRangeMax"), port_min=rule.get("portRangeMin"))

                    if rule.get("remoteIp") and "/" in rule.get("remoteIp"):
                        sl_security_group_rule.rule_type = "cidr_block"
                        sl_security_group_rule.cidr_block = rule.get("remoteIp")

                    elif rule.get("remoteIp"):
                        sl_security_group_rule.rule_type = "address"
                        sl_security_group_rule.address = rule.get("remoteIp")

                    sl_security_group.rules.append(sl_security_group_rule)
                sl_security_groups_list.append(sl_security_group)

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
        else:
            return sl_security_groups_list

    def list_images(self) -> dict:
        """List all private and public images on the Account as Dict."""
        try:

            self.image_manager = ImageManager(self.client)
            return {
                "private_images": self.retry.call(self.image_manager.list_private_images),
                "public_images": self.retry.call(self.image_manager.list_public_images),
            }

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def list_private_images_name(self):
        """List all private and public images on the Account as Dict."""
        image_list = list()
        try:
            # TODO we should ask region from the user and send the exact name rather then first element
            self.image_manager = ImageManager(self.client)
            images = self.retry.call(self.image_manager.list_private_images, mask=IMAGE_MASK)
            for image in images:
                if not image.get("children"):
                    continue

                image_child = image["children"][0]
                if image_child.get('transactionId'):
                    continue

                if not image_child.get("blockDevices"):
                    continue

                block_device = image_child["blockDevices"][0]
                if not block_device.get("diskImage"):
                    continue

                disk_image = block_device.get("diskImage")
                if not disk_image.get('softwareReferences'):
                    continue

                software_reference = disk_image["softwareReferences"][0]
                if not (software_reference.get("softwareDescription") and software_reference.get(
                        "softwareDescription").get("longDescription")):
                    continue

                image_name = software_reference.get("softwareDescription").get("longDescription")
                instance_vpc_image = classical_vpc_image_dictionary.get(image_name)
                instance_vpc_image = instance_vpc_image[0] if instance_vpc_image else "-"
                if instance_vpc_image == "-":
                    continue

                image_list.append({
                    "id": image.get('id'),
                    "name": image.get('name'),
                    "vpc_image_name": instance_vpc_image,
                    "operating_systems": {
                        "architecture": "amd64"
                    }
                })

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
        else:
            return image_list

    def list_vsi_hostnames(self) -> List[Dict]:
        """List all private and public images on the Account as Dict."""
        instances_list = list()
        try:
            self.vs_manager = VSManager(self.client)
            instances = self.retry.call(self.vs_manager.list_instances, mask=VSI_ID_HOSTNAME_ONLY_MASK)
            for instance in instances:
                instances_list.append({
                    "id": instance.get('id'),
                    "hostname": instance.get('hostname')
                })
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
        else:
            return instances_list

    def list_dedicated_hosts(self, instances=False, raw=False) -> List[Dict]:
        """List all Dedicated Hosts on the Account as Dict."""
        try:
            self.dedicated_host_manager = DedicatedHostManager(self.client)
            dedicated_hosts = self.retry.call(
                self.dedicated_host_manager.list_instances,
                mask=DEDICATED_HOST_W_INSTANCES_MASK if instances else DEDICATED_HOST_WO_INSTANCES_MASK
            )
            dedicated_hosts_list = dedicated_hosts
            if not raw:
                dedicated_hosts_list = [
                    SoftLayerDedicatedHost.from_softlayer_json(dedicated_host) for dedicated_host in dedicated_hosts
                ]
        except SoftLayerAPIError as ex:
            LOGGER.info(f"error_message => {ex.reason}")
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
        else:
            return dedicated_hosts_list

    def list_ssh_keys(self) -> list:
        """Lists all SSH keys on the Account."""
        try:
            self.ssh_manager = SshKeyManager(self.client)
            return self.retry.call(self.ssh_manager.list_keys)
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def list_ssl_certs(self) -> dict:
        """A list of dictionaries representing the requested SSL certs."""
        try:
            self.ssl_manager = SSLManager(self.client)
            return self.retry.call(self.ssl_manager.list_certs)
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def get_classic_image_name(self, image_name):
        """concatenate an integer value if this image already exists"""
        try:
            img_manager = ImageManager(self.client)
            private_images = self.retry.call(img_manager.list_private_images, name=image_name)
            num = 1
            while True:
                if image_name not in [image.get("name") for image in private_images]:
                    return image_name
                image_name = "-".join([image_name, str(num)])
                num += 1

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def list_kubernetes_clusters(self, user_name, api_key):
        """List Classic IKS Clusters on the Account."""
        try:
            iks_clusters_list = list()
            kubernetes_client = ClassicKubernetesClient(user_name, api_key)
            clusters = kubernetes_client.list_clusters()

            if clusters:
                for cluster in clusters:
                    multi_zone_cluster = False
                    free_tier_cluster = False

                    if cluster['state'] != "normal" or cluster['type'] == "openshift":
                        continue
                    k8s_cluster = KubernetesCluster.from_ibm_json_body(cluster)
                    k8s_cluster.status = CREATION_PENDING
                    k8s_cluster_worker_pools = kubernetes_client.get_cluster_worker_pool(cluster["id"])

                    for k8s_cluster_worker_pool in k8s_cluster_worker_pools:
                        if len(k8s_cluster_worker_pool['zones']) > 1:
                            multi_zone_cluster = True
                            break
                        classic_k8s_cluster_worker_pool = KubernetesClusterWorkerPool.from_ibm_json_body(
                            k8s_cluster_worker_pool)

                        for k8s_cluster_worker_pool_zone in k8s_cluster_worker_pool['zones']:
                            classic_k8s_cluster_worker_pool_zone = KubernetesClusterWorkerPoolZone.from_ibm_json_body(
                                k8s_cluster_worker_pool_zone)
                            k8s_cluster_subnets = kubernetes_client.get_cluster_subnets(cluster["id"],
                                                                                        cluster["resourceGroup"])
                            if k8s_cluster_subnets == "Free tier cluster":
                                free_tier_cluster = True
                                break
                            subnets = self.list_private_subnets()
                            for subnet in subnets:
                                for k8s_cluster_subnet in k8s_cluster_subnets:
                                    if classic_k8s_cluster_worker_pool_zone.private_vlan == k8s_cluster_subnet["id"]:
                                        if subnet.network == k8s_cluster_subnet["subnets"][0]['cidr']:
                                            classic_k8s_cluster_worker_pool_zone.subnets.append(subnet.to_ibm())
                                classic_k8s_cluster_worker_pool.zones.append(classic_k8s_cluster_worker_pool_zone)
                            k8s_cluster.worker_pools.append(classic_k8s_cluster_worker_pool)

                    if multi_zone_cluster:
                        continue
                    if free_tier_cluster:
                        continue

                    kube_config = kubernetes_client.get_cluster_kube_config(cluster["id"])
                    kube_config = K8s(configuration_json=kube_config)
                    workloads = list()
                    namespaces = kube_config.client.CoreV1Api().list_namespace()

                    for namespace in namespaces.items:
                        kubernetes_objects = {"pod": list(), "svc": list(), "pvc": list()}
                        if namespace.metadata.name in ["kube-system", "kube-public", "ibm-cert-store", "ibm-operators",
                                                       "kube-node-lease", "ibm-system", "ibm-observe"]:
                            continue

                        kubernetes_objects["namespace"] = namespace.metadata.name
                        pods = kube_config.client.CoreV1Api().list_namespaced_pod(namespace=namespace.metadata.name)
                        if pods.items:
                            for pod in pods.items:
                                kubernetes_objects["pod"].append(pod.metadata.name)

                        svcs = kube_config.client.CoreV1Api().list_namespaced_service(namespace=namespace.metadata.name)
                        if svcs.items:
                            for svc in svcs.items:
                                kubernetes_objects["svc"].append(svc.metadata.name)

                        pvcs = kube_config.client.CoreV1Api().list_namespaced_persistent_volume_claim(
                            namespace=namespace.metadata.name)
                        if pvcs.items:
                            for pvc in pvcs.items:
                                kubernetes_objects["pvc"].append({"name": pvc.metadata.name,
                                                                  "size": pvc.spec.resources.requests['storage']})

                        workloads.append(kubernetes_objects)

                    k8s_cluster.workloads = workloads
                    iks_clusters_list.append(k8s_cluster)

            return iks_clusters_list

        except Exception as ex:
            LOGGER.info(ex)
