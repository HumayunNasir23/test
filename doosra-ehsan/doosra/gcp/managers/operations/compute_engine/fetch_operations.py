import re

from google.auth.exceptions import RefreshError, TransportError, DefaultCredentialsError
from googleapiclient.errors import HttpError, UnexpectedBodyError, UnexpectedMethodError

from doosra.gcp.managers.consts import DEFAULT_IMAGES_PROJECTS
from doosra.gcp.managers.exceptions import *
from doosra.models.gcp_models import GcpAddress, GcpBackend, GcpBackendService, GcpDisk, GcpFirewallRule, \
    GcpForwardingRule, GcpPortHealthCheck, GcpHealthCheck, GcpHostRule, GcpIpProtocol, GcpPathMatcher, GcpPathRule, \
    GcpInstance, GcpInstanceGroup, GcpLoadBalancer, GcpNetworkInterface, GcpSubnet, GcpSecondaryIpRange, GcpTag, \
    GcpTargetProxy, GcpVpcNetwork, GcpUrlMap, InstanceDisk


class FetchOperations(object):
    def __init__(self, cloud, service):
        self.cloud = cloud
        self.service = service

    def get_regions(self, project_id, name=None):
        """
        Retrieves the list of region resources available to the specified project.
        :return:
        """
        regions_list = list()
        request = self.service.regions().list(project=project_id)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for region in response.get('items'):
                if name and name != region.get('name'):
                    continue

                regions_list.append(region.get('name'))

            request = self.service.regions().list_next(previous_request=request, previous_response=response)
        return regions_list

    def get_vpc_networks(self, project_id, name=None):
        """
        Get all VPC networks in the specified project
        :param name: name of VPC network <OPTIONAL>
        :param project_id: projectID
        :return:
        """
        vpc_networks = list()
        request = self.service.networks().list(project=project_id)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for network in response.get('items'):
                if name and name != network.get('name'):
                    continue

                vpc_network = GcpVpcNetwork(name=network.get("name"), description=network.get("description"),
                                            auto_create_subnetworks=network.get("autoCreateSubnetworks") or False,
                                            routing_mode=network["routingConfig"]["routingMode"])
                if network.get("subnetworks"):
                    for subnet in network.get("subnetworks"):
                        subnet_split = subnet.split('/')
                        subnet_obj = self.get_vpc_subnets(project_id=project_id, region=subnet_split[-3],
                                                          name=subnet_split[-1])
                        if subnet_obj:
                            vpc_network.subnets.append(subnet_obj[0])

                vpc_networks.append(vpc_network)
            request = self.service.networks().list_next(previous_request=request, previous_response=response)

        return vpc_networks

    def get_vpc_subnets(self, project_id, region, name=None, ip_cidr_range=None):
        """
        Retrieves a list of subnetworks available to the specified project.
        :param region: name of the region
        :param project_id: project_id for this request
        :param name: name of the VPC subnet
        :param ip_cidr_range: IPV4 CIDR range for subnet
        :return:
        """
        vpc_subnets = list()
        request = self.service.subnetworks().list(project=project_id, region=region)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for subnetwork in response['items']:
                if name and name != subnetwork.get('name'):
                    continue

                region_name_split = subnetwork.get("region").split('/')
                subnet = GcpSubnet(name=subnetwork.get("name"), ip_cidr_range=subnetwork.get('ipCidrRange'),
                                   region=region_name_split[-1],
                                   enable_flow_logs=subnetwork.get('enableFlowLogs'),
                                   private_google_access=subnetwork.get('privateIpGoogleAccess'),
                                   description=subnetwork.get('description'))
                if subnetwork.get('secondaryIpRanges'):
                    for ip_range in subnetwork.get('secondaryIpRanges'):
                        secondary_ip_range = GcpSecondaryIpRange(name=ip_range.get('rangeName'),
                                                                 ip_cidr_range=ip_range.get('ipCidrRange'))
                        subnet.secondary_ip_ranges.append(secondary_ip_range)

                if not (ip_cidr_range and ip_cidr_range != subnet.ip_cidr_range):
                    vpc_subnets.append(subnet)

            request = self.service.subnetworks().list_next(previous_request=request, previous_response=response)

        return vpc_subnets

    def get_all_vpc_subnets(self, project_id, name=None):
        """
        Get all VPC subnets defined in a project, regardless of a region
        :param project_id: Project ID for this request
        :param name: name of subnetwork
        :return:
        """
        subnets_list = list()
        request = self.service.subnetworks().aggregatedList(project=project_id)
        while request is not None:
            response = self.execute(request)
            for _, subnetworks in response['items'].items():
                if not subnetworks.get("subnetworks"):
                    continue

                for subnetwork in subnetworks.get("subnetworks"):
                    if name and name != subnetwork.get("name"):
                        continue

                    region_name_split = subnetwork.get("region").split('/')
                    subnet = GcpSubnet(name=subnetwork.get("name"), ip_cidr_range=subnetwork.get('ipCidrRange'),
                                       region=region_name_split[-1], enable_flow_logs=subnetwork.get('enableFlowLogs'),
                                       private_google_access=subnetwork.get('privateIpGoogleAccess'),
                                       description=subnetwork.get('description'))
                    if subnetwork.get('secondaryIpRanges'):
                        for ip_range in subnetwork.get('secondaryIpRanges'):
                            secondary_ip_range = GcpSecondaryIpRange(name=ip_range.get('rangeName'),
                                                                     ip_cidr_range=ip_range.get('ipCidrRange'))
                            subnet.secondary_ip_ranges.append(secondary_ip_range)

                    subnets_list.append(subnet)
            request = self.service.subnetworks().aggregatedList_next(previous_request=request,
                                                                     previous_response=response)
        return subnets_list

    def get_vpc_subnet_fingerprint(self, project_id, region, subnet):
        """
        Get latest subnet fingerprint value. This will be used when making a patch call to update Subnet.
        :return:
        """
        request = self.service.subnetworks().get(project=project_id, region=region, subnetwork=subnet)
        response = self.execute(request)
        if not response:
            return

        return response.get('fingerprint')

    def get_addresses(self, project_id, region=None, name=None):
        """
        Retrieves a list of global or regional addresses.
        :return:
        """
        address_list = list()
        if region:
            request = self.service.addresses().list(project=project_id, region=region)
        else:
            request = self.service.globalAddresses().list(project=project_id)

        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for address in response['items']:
                if name and name != address["name"]:
                    continue

                address_obj = GcpAddress(name=address['name'], type_=address.get('addressType'),
                                         address=address.get('address'), ip_version=address.get('ipVersion'),
                                         description=address.get('description'))
                if address.get('region'):
                    region_name_split = address.get('region').split('/')
                    address_obj.region = region_name_split[-1]
                address_list.append(address_obj)

            if region:
                request = self.service.addresses().list_next(previous_request=request, previous_response=response)
            else:
                request = self.service.globalAddresses().list_next(previous_request=request, previous_response=response)

        return address_list

    def get_zones(self, project_id, name=None):
        """
        Retrieves the list of zones resources available to the specified project.
        :return:
        """
        zones_list = list()
        request = self.service.zones().list(project=project_id)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for zone in response.get('items'):
                if name and name != zone.get('name'):
                    continue

                region_name_split = zone.get('region').split('/')
                zones_list.append({
                    "name": zone.get('name'),
                    "region": region_name_split[-1],
                    "status": zone.get("status")
                })
            request = self.service.zones().list_next(previous_request=request, previous_response=response)
        return zones_list

    def get_all_images(self, project_id):
        """
        Get all images including default images provided by Google cloud
        :param project_id:
        :return:
        """
        images_list = self.get_images(project_id)
        for project in DEFAULT_IMAGES_PROJECTS:
            for family in project[1:]:
                image = self.get_latest_images(project[0], family)
                if image:
                    images_list.append(image)

        return images_list

    def get_images(self, project_id, name=None):
        """
        Retrieves the list of images resources available to the specified project.
        Call this method to get default images by changing project_id i.e debian-cloud or windows-cloud
        :return:
        """
        image_list = list()
        request = self.service.images().list(project=project_id)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for image in response.get('items'):
                if name and name != image.get('name'):
                    continue

                image_list.append('projects/{project}/global/images/{name}'.format(
                    project=project_id, name=image.get('name')))
            request = self.service.images().list_next(previous_request=request, previous_response=response)
        return image_list

    def get_latest_images(self, project_id, family):
        """
        Returns the latest image that is part of an image family and is not deprecated.
        :return:
        """
        request = self.service.images().getFromFamily(project=project_id, family=family)
        response = self.execute(request)
        if response:
            image = 'projects/{project}/global/images/{name}'.format(project=project_id, name=response.get('name'))
            return image

    def get_machine_types(self, project_id, name=None):
        """
        Retrieves the list of machine types resources available to the specified project.
        :return:
        """
        mtype_list = list()
        request = self.service.machineTypes().aggregatedList(project=project_id)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for zone, machine_types in response.get('items').items():
                if not machine_types.get("machineTypes"):
                    continue

                zone = zone.split('/')
                mtypes_zone = {"zone": zone[-1], "machine_types": []}
                for machine_type in machine_types.get("machineTypes"):
                    if name and name != machine_type.get("name"):
                        continue

                    mtypes_zone["machine_types"].append({
                        "name": machine_type.get('name'),
                        "description": machine_type.get('description'),
                        "guest_cpus": machine_type.get('guestCpus'),
                        "memory_mb": machine_type.get('memoryMb'),
                        "image_space_gb": machine_type.get('imageSpaceGb'),
                        "max_persistent_disks": machine_type.get('maximumPersistentDisks'),
                        "max_persistent_disks_size_gb": machine_type.get('maximumPersistentDisksSizeGb'),
                        "is_shared_cpu": machine_type.get('isSharedCpu')
                    })

                mtype_list.append(mtypes_zone)
            request = self.service.machineTypes().aggregatedList_next(previous_request=request,
                                                                      previous_response=response)
        return mtype_list

    def get_all_disks(self, project_id, name=None):
        """
        Get all disks in the specified project
        :param project_id: projectID
        :param name: name of the disk <OPTIONAL>
        :return: list of GcpDisk objects
        """
        disks_list = list()
        request = self.service.disks().aggregatedList(project=project_id)

        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for zone, disks in response.get('items').items():
                if not disks.get("disks"):
                    continue

                for disk in disks.get("disks"):
                    if name and name != disk.get("name"):
                        continue

                    zone_name_split = disk.get("zone").split("/")
                    source_image_split = disk.get("sourceImage").split("/")
                    disk_type_split = disk.get("type").split("/")
                    gcp_disk = GcpDisk(name=disk.get("name"), zone=zone_name_split[-1], disk_type=disk_type_split[-1],
                                       disk_size=disk.get("sizeGb"), source_image='/'.join(source_image_split[5:]))
                    disks_list.append(gcp_disk)
            request = self.service.disks().aggregatedList_next(previous_request=request, previous_response=response)

        return disks_list

    def get_disks(self, project_id, zone, name=None):
        """
        Get all disks in the specified project and in a specified zone
        :param project_id: projectID
        :param zone: name of the zone to find the disk in
        :param name: name of the disk <OPTIONAL>
        :return: list of GcpDisk objects
        """
        disks_list = list()
        request = self.service.disks().list(project=project_id, zone=zone)

        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for disk in response.get("items"):
                if name and name != disk.get("name"):
                    continue

                zone_name_split = disk.get('zone').split('/')
                disk_type_split = disk.get("type").split('/')
                source_image_split = disk.get("sourceImage").split('v1/')
                gcp_disk = GcpDisk(name=disk.get("name"), zone=zone_name_split[-1], disk_type=disk_type_split[-1],
                                   disk_size=disk.get("sizeGb"), source_image=source_image_split[-1])
                disks_list.append(gcp_disk)
            request = self.service.disks().list_next(previous_request=request, previous_response=response)

        return disks_list

    def get_all_instances(self, project_id, name=None, vpc_network=None):
        """
        Get all instances in the specified project
        :param project_id: projectID
        :param name: name of the Instance <OPTIONAL>
        :return: list of GcpInstance objects
        """
        instances_list = list()
        request = self.service.instances().aggregatedList(project=project_id)

        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for _, instances in response.get('items').items():
                if not instances.get("instances"):
                    continue

                for instance in instances.get("instances"):
                    if name and name != instance.get("name"):
                        continue

                    zone_name_split = instance.get('zone').split('/')
                    machine_type_split = instance.get('machineType').split('/')
                    gcp_instance = GcpInstance(name=instance.get("name"), description=instance.get("description"),
                                               machine_type=machine_type_split[-1], zone=zone_name_split[-1],
                                               cloud_project_id=project_id)
                    if instance.get('tags').get('items'):
                        for tag in instance.get('tags').get('items'):
                            gcp_tag = GcpTag(tag=tag)
                            gcp_instance.tags.append(gcp_tag)

                    for interface in instance.get("networkInterfaces"):
                        gcp_network_interface = GcpNetworkInterface(
                            name=interface.get("name"), primary_internal_ip=interface.get("networkIP"),
                            external_ip=interface.get("accessConfigs")[0].get("natIP") if interface.get(
                                "accessConfigs") else None)
                        if interface.get('network'):
                            network_name_split = interface.get('network').split('/')
                            if vpc_network and vpc_network != network_name_split[-1]:
                                continue

                            vpc_network = self.get_vpc_networks(project_id, name=network_name_split[-1])
                            if vpc_network:
                                gcp_network_interface.gcp_vpc_network = vpc_network[0]
                                subnetwork_split = interface.get('subnetwork').split('/')
                                for subnet in vpc_network[0].subnets.all():
                                    if subnetwork_split[-1] == subnet.name:
                                        gcp_network_interface.gcp_subnet = subnet
                                        break

                        gcp_instance.interfaces.append(gcp_network_interface)

                    for disk in instance.get("disks"):
                        gcp_disk = self.get_disks(project_id, zone_name_split[-1], disk.get("source").split("/")[-1])[
                            0]
                        gcp_disk.instance_disk = InstanceDisk()
                        gcp_disk.instance_disk.boot = disk.get("boot")
                        gcp_disk.instance_disk.auto_delete = disk.get("autoDelete")
                        gcp_disk.instance_disk.mode = disk.get("mode")
                        gcp_instance.disks.append(gcp_disk)

                    instances_list.append(gcp_instance)
            request = self.service.instances().aggregatedList_next(previous_request=request, previous_response=response)

        return instances_list

    def get_instances(self, project_id, zone, name=None, vpc_network=None):
        """
        Retrieves the list of instances in a zone of a specified project.
        :param project_id: project in which to find instances
        :param zone: zone in which to find instances
        :param name: name of the instance <OPTIONAL>
        :param vpc_network: name of the VPC network <OPTIONAL>
        :return: list of GcpInstance objects
        """
        instance_list = list()
        request = self.service.instances().list(project=project_id, zone=zone)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for instance in response.get('items'):
                if name and name != instance.get('name'):
                    continue

                zone_name_split = instance.get('zone').split('/')
                machine_type_split = instance.get('machineType').split('/')
                gcp_instance = GcpInstance(name=instance.get("name"), description=instance.get("description"),
                                           machine_type=machine_type_split[-1], zone=zone_name_split[-1])
                if instance.get('tags').get('items'):
                    for tag in instance.get('tags').get('items'):
                        gcp_tag = GcpTag(tag=tag)
                        gcp_instance.tags.append(gcp_tag)

                for interface in instance.get("networkInterfaces"):
                    gcp_network_interface = GcpNetworkInterface(
                        name=interface.get("name"), primary_internal_ip=interface.get("networkIP"),
                        external_ip=interface.get("accessConfigs")[0].get("natIP") if interface.get(
                            "accessConfigs") else None)
                    if interface.get('network'):
                        network_name_split = interface.get('network').split('/')
                        if vpc_network and vpc_network != network_name_split[-1]:
                            continue

                        vpc_network = self.get_vpc_networks(project_id, name=network_name_split[-1])
                        if vpc_network:
                            gcp_network_interface.gcp_vpc_network = vpc_network[0]
                            subnetwork_split = interface.get('subnetwork').split('/')
                            for subnet in vpc_network[0].subnets.all():
                                if subnetwork_split[-1] == subnet.name:
                                    gcp_network_interface.gcp_subnet = subnet
                                    break

                    gcp_instance.interfaces.append(gcp_network_interface)

                for disk in instance.get("disks"):
                    gcp_disk = self.get_disks(project_id, zone.strip("zones/"), disk.get("source").split("/")[-1])[0]
                    gcp_disk.instance_disk = InstanceDisk()
                    gcp_disk.instance_disk.boot = disk.get("boot")
                    gcp_disk.instance_disk.auto_delete = disk.get("autoDelete")
                    gcp_disk.instance_disk.mode = disk.get("mode")
                    gcp_instance.disks.append(gcp_disk)

                instance_list.append(gcp_instance)
            request = self.service.instances().list_next(previous_request=request, previous_response=response)
        return instance_list

    def get_firewall_rules(self, project_id, name=None, vpc_network=None):
        """
        Retrieves the list of firewall rules available to the specified project.
        :param project_id: Project ID for this request.
        :param name: name of firewall rule
        :param vpc_network: name of VPC network
        :return:
        """
        firewall_rules_list = list()
        request = self.service.firewalls().list(project=project_id)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for firewall in response.get('items'):
                if name and name != firewall.get('name'):
                    continue

                ip_protocols, ip_ranges, tags, action = list(), list(), list(), None
                if firewall.get("allowed"):
                    action = "ALLOW"
                    for protocol in firewall.get("allowed"):
                        ip_protocol = GcpIpProtocol(protocol.get('IPProtocol'), ports=protocol.get('ports'))
                        ip_protocols.append(ip_protocol)
                elif firewall.get("denied"):
                    action = "DENY"
                    for protocol in firewall.get("denied"):
                        ip_protocol = GcpIpProtocol(protocol.get('IPProtocol'), ports=protocol.get('ports'))
                        ip_protocols.append(ip_protocol)

                if firewall.get('direction') == "INGRESS":
                    ip_ranges = firewall.get('sourceRanges')
                elif firewall.get('direction') == "EGRESS":
                    ip_ranges = firewall.get('destinationRanges')

                firewall_rule = GcpFirewallRule(name=firewall.get('name'), action=action,
                                                direction=firewall.get('direction'),
                                                priority=firewall.get('priority'),
                                                description=firewall.get('description'), ip_ranges=ip_ranges)
                firewall_rule.ip_protocols = ip_protocols
                network_name = firewall.get('network').split('/')
                if vpc_network and vpc_network != network_name[-1]:
                    continue

                network = self.get_vpc_networks(project_id, network_name[-1])
                network = network[0] if network else None
                firewall_rule.gcp_vpc_network = network

                if firewall.get('targetTags'):
                    for target_tag in firewall.get('targetTags'):
                        gcp_target_tag = GcpTag(target_tag)
                        gcp_target_tag.gcp_vpc_network = network
                        firewall_rule.target_tags.append(gcp_target_tag)

                if firewall.get('sourceTags'):
                    for tag in firewall.get('sourceTags'):
                        gcp_tag = GcpTag(tag)
                        gcp_tag.gcp_vpc_network = network
                        firewall_rule.tags.append(gcp_tag)

                firewall_rules_list.append(firewall_rule)
            request = self.service.firewalls().list_next(previous_request=request, previous_response=response)
        return firewall_rules_list

    def get_instance_groups(self, project_id, zone, name=None):
        """
        Retrieves the list of instance groups that are located in the specified project and zone.
        :return:
        """
        instance_groups_list = list()
        request = self.service.instanceGroups().list(project=project_id, zone=zone)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for instance_group in response['items']:
                if name and name != instance_group.get('name'):
                    continue

                gcp_instance_group = GcpInstanceGroup(instance_group.get('name'), zone,
                                                      instance_group.get('description'))
                network_name_split = instance_group.get('network').split('/')
                networks = self.get_vpc_networks(project_id, network_name_split[-1])
                if networks:
                    gcp_instance_group.gcp_vpc_network = networks[0]
                instance_groups_list.append(gcp_instance_group)
            request = self.service.instanceGroups().list_next(previous_request=request, previous_response=response)
        return instance_groups_list

    def get_all_instance_groups(self, project_id, name=None):
        """
        Retrieves the list of instance groups that are located in the specified project.
        :return:
        """
        instance_groups_list = list()
        request = self.service.instanceGroups().aggregatedList(project=project_id)
        while request is not None:
            response = self.execute(request)
            for _, instance_groups in response['items'].items():
                if not instance_groups.get("instanceGroups"):
                    continue

                for instance_group in instance_groups.get("instanceGroups"):
                    if name and name != instance_group.get('name'):
                        continue

                    zone_name_split = instance_group.get('zone').split('/')
                    gcp_instance_group = GcpInstanceGroup(instance_group.get('name'), zone_name_split[-1],
                                                          instance_group.get('description'))
                    network_name_split = instance_group.get('network').split('/')
                    networks = self.get_vpc_networks(project_id, network_name_split[-1])
                    if networks:
                        gcp_instance_group.gcp_vpc_network = networks[0]
                    instance_groups_list.append(gcp_instance_group)

            request = self.service.instanceGroups().aggregatedList_next(previous_request=request,
                                                                        previous_response=response)
        return instance_groups_list

    def get_instance_group_instances(self, project_id, zone, instance_group_name):
        """
        Lists the instances in the specified instance group.
        :return:
        """
        instances_list = list()
        request = self.service.instanceGroups().listInstances(project=project_id, zone=zone,
                                                              instanceGroup=instance_group_name, body="")
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for instance in response['items']:
                instance_name_split = instance.get('instance').split('/')
                instances_list.append(instance_name_split[-1])

            request = self.service.instanceGroups().listInstances_next(previous_request=request,
                                                                       previous_response=response)
        return instances_list

    def get_backend_services(self, project_id, name=None):
        """
        Returns the specified BackendService resource. Gets a list of available backend services.
        :return:
        """
        backend_services_list = list()
        request = self.service.backendServices().list(project=project_id)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for backend_service in response['items']:
                if name and name != backend_service.get('name'):
                    continue

                gcp_backend_service = GcpBackendService(backend_service.get('name'), backend_service.get('protocol'),
                                                        backend_service.get('portName'), backend_service.get('port'),
                                                        backend_service.get('timeoutSec'),
                                                        backend_service.get('description'),
                                                        backend_service.get('enableCDN'))
                if backend_service.get('backends'):
                    for backend in backend_service.get('backends'):
                        gcp_backend = GcpBackend(backend.get('maxUtilization'), backend.get('capacityScaler'),
                                                 backend.get('description'))
                        group_name_split = backend.get('group').split('/')
                        instance_groups = self.get_all_instance_groups(project_id, group_name_split[-1])
                        if instance_groups:
                            gcp_backend.instance_group = instance_groups[0]
                        gcp_backend_service.backends.append(gcp_backend)
                if backend_service.get('healthChecks'):
                    for health_check in backend_service.get('healthChecks'):
                        health_check_name_split = health_check.split('/')
                        health_checks = self.get_health_checks(project_id, health_check_name_split[-1])
                        if health_checks:
                            gcp_backend_service.health_check = health_checks[0]
                backend_services_list.append(gcp_backend_service)
            request = self.service.backendServices().list_next(previous_request=request, previous_response=response)
        return backend_services_list

    def get_health_checks(self, project_id, name=None):
        """
        An HealthCheck resource. This resource defines a template for how individual virtual machines should be
        checked for health, via one of the supported protocols.
        :return:
        """
        health_check_list = list()
        request = self.service.healthChecks().list(project=project_id)
        while request is not None:
            response = self.execute(request)
            if not response.get('items'):
                break

            for health_check in response['items']:
                if name and name != health_check.get('name'):
                    continue

                gcp_health_check = GcpHealthCheck(health_check.get('name'), health_check.get('type'),
                                                  health_check.get('description'),
                                                  health_check.get('healthyThreshold'),
                                                  health_check.get('unhealthyThreshold'),
                                                  health_check.get('timeoutSec'),
                                                  health_check.get('checkIntervalSec'))
                port_health_check = health_check.get("{}HealthCheck".format(health_check.get('type').lower()))
                if port_health_check:
                    gcp_port_health_check = GcpPortHealthCheck(port_health_check.get('port'),
                                                               port_health_check.get('request'),
                                                               port_health_check.get('response'),
                                                               port_health_check.get('proxyHeader'))
                    gcp_health_check.port_health_check = gcp_port_health_check
                health_check_list.append(gcp_health_check)
            request = self.service.healthChecks().list_next(previous_request=request, previous_response=response)
        return health_check_list

    def get_forwarding_rules(self, project_id, name=None, type_="GLOBAL"):
        """
        Get a list of Forwarding Rules configured in a project. A ForwardingRule resource specifies which pool of
        target virtual machines to forward a packet to if it matches the given [IPAddress, IPProtocol, ports] tuple.
        :return:
        """
        forwarding_rules_list = list()
        request = self.service.globalForwardingRules().list(project=project_id)
        while request is not None:
            response = request.execute()
            if not response.get('items'):
                break

            for forwarding_rule in response.get('items'):
                if name and name != forwarding_rule.get('name'):
                    continue

                gcp_forwarding_rule = GcpForwardingRule(name=forwarding_rule.get('name'),
                                                        description=forwarding_rule.get('description'),
                                                        ip_address=forwarding_rule.get('IPAddress'),
                                                        ip_protocol=forwarding_rule.get('IPProtocol'),
                                                        port_range=forwarding_rule.get('portRange'),
                                                        load_balancing_scheme=forwarding_rule.get(
                                                            'loadBalancingScheme'))
                if forwarding_rule.get('target'):
                    target_name_split = forwarding_rule.get('target').split('/')
                    target_type = re.search('target(.+?)Proxies', target_name_split[-2])
                    if target_type:
                        target = self.get_target_proxies(project_id, target_type.group(1).upper(),
                                                         target_name_split[-1])
                        if target:
                            gcp_forwarding_rule.target_proxy = target[0]
                forwarding_rules_list.append(gcp_forwarding_rule)
            request = self.service.globalForwardingRules().list_next(previous_request=request,
                                                                     previous_response=response)
        return forwarding_rules_list

    def get_target_proxies(self, project_id, type_, name=None):
        """
        Retrieves the list of proxy resources available to the specified project.
        """
        target_proxies, service = list(), None
        if type_ == "HTTP":
            service = self.service.targetHttpProxies()
        elif type_ == "HTTPS":
            service = self.service.targetHttpsProxies()

        if not service:
            return

        request = service.list(project=project_id)

        while request is not None:
            response = request.execute()
            if not response.get('items'):
                break

            for target_proxy in response.get('items'):
                if name and name != target_proxy.get('name'):
                    continue

                url_map_split = target_proxy.get('urlMap').split('/')
                gcp_target_proxy = GcpTargetProxy(target_proxy.get('name'), type_)
                url_map = self.get_url_maps(project_id, url_map_split[-1])
                if url_map:
                    gcp_target_proxy.url_map = url_map[0]
                target_proxies.append(gcp_target_proxy)

            request = service.list_next(previous_request=request, previous_response=response)
        return target_proxies

    def get_url_maps(self, project_id, name=None):
        """
        Retrieves the list of UrlMap resources available to the specified project.
        :return:
        """
        url_maps = list()
        request = self.service.urlMaps().list(project=project_id)
        while request is not None:
            response = request.execute()
            if not response.get('items'):
                break

            for url_map in response.get('items'):
                if name and name != url_map.get('name'):
                    continue

                gcp_url_map = GcpUrlMap(url_map.get('name'), url_map.get('description'))
                if url_map.get('defaultService'):
                    service_name_split = url_map.get('defaultService').split('/')
                    service = self.get_backend_services(project_id, service_name_split[-1])
                    if service:
                        gcp_url_map.default_backend_service = service[0]
                if url_map.get('hostRules'):
                    for host_rule in url_map.get('hostRules'):
                        gcp_host_rule = GcpHostRule(host_rule.get('hosts'))
                        path_matcher_name = host_rule.get('pathMatcher')
                        if url_map.get('pathMatchers'):
                            for path_matcher in url_map.get('pathMatchers'):
                                if path_matcher_name != path_matcher.get('name'):
                                    continue

                                gcp_path_matcher = GcpPathMatcher(path_matcher.get('name'),
                                                                  path_matcher.get('description'))
                                default_service_name = path_matcher.get('defaultService').split('/')
                                default_service = self.get_backend_services(project_id, default_service_name[-1])
                                if default_service:
                                    gcp_path_matcher.default_backend_service = default_service[0]
                                if path_matcher.get('pathRules'):
                                    for path_rule in path_matcher.get('pathRules'):
                                        service_name_split = path_rule.get('service').split('/')
                                        gcp_path_rule = GcpPathRule(path_rule.get('paths'))
                                        service = self.get_backend_services(project_id, service_name_split[-1])
                                        if service:
                                            gcp_path_rule.service = service[0]
                                        gcp_path_matcher.path_rules.append(gcp_path_rule)
                                gcp_host_rule.path_matcher = gcp_path_matcher
                            gcp_url_map.host_rules.append(gcp_host_rule)

                url_maps.append(gcp_url_map)

            request = self.service.urlMaps().list_next(previous_request=request, previous_response=response)

        return url_maps

    def get_load_balancers(self, project_id, name=None):
        """
        Get load balancers configured in a Google Cloud Project
        :return:
        """
        load_balancers_list, lb_forwarding_rules_dict = list(), dict()
        for forwarding_rule in self.get_forwarding_rules(project_id, type_="GLOBAL"):
            if not (forwarding_rule.target_proxy and forwarding_rule.target_proxy.url_map):
                continue

            if forwarding_rule.target_proxy.url_map.name not in lb_forwarding_rules_dict.keys():
                lb_forwarding_rules_dict[forwarding_rule.target_proxy.url_map.name] = list()

            lb_forwarding_rules_dict[forwarding_rule.target_proxy.url_map.name].append(forwarding_rule)

        for load_balancer in lb_forwarding_rules_dict:
            if name and name != load_balancer:
                continue
            gcp_load_balancer = GcpLoadBalancer(name=load_balancer)
            for forwarding_rule_ in lb_forwarding_rules_dict[load_balancer]:
                gcp_load_balancer.url_map = forwarding_rule_.target_proxy.url_map
                if not gcp_load_balancer.url_map.default_backend_service:
                    continue

                gcp_load_balancer.backend_services.append(gcp_load_balancer.url_map.default_backend_service)
                gcp_load_balancer.forwarding_rules.append(forwarding_rule_)
            load_balancers_list.append(gcp_load_balancer)
        return load_balancers_list

    def execute(self, request):
        """
        Executes request object on GCP cloud account and returns the response.
        :param request:
        :return:
        """
        try:
            response = request.execute()
        except (DefaultCredentialsError, HttpError, UnexpectedBodyError, UnexpectedMethodError, RefreshError,
                TransportError) as ex:
            if isinstance(ex, (UnexpectedBodyError, UnexpectedMethodError)):
                raise CloudInvalidRequestError(self.cloud.id)
            elif isinstance(ex, HttpError):
                raise CloudExecuteError(ex)
            elif isinstance(ex, (RefreshError, DefaultCredentialsError, TransportError)):
                raise CloudAuthError(self.cloud.id)
        else:
            return response
