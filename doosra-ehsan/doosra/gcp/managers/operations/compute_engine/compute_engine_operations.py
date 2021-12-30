import time

from google.auth.exceptions import RefreshError, TransportError, DefaultCredentialsError
from googleapiclient import discovery
from googleapiclient.errors import HttpError, UnexpectedBodyError, UnexpectedMethodError

from doosra.gcp.managers.consts import COMPUTE_ENGINE_SERVICE_NAME
from doosra.gcp.managers.consts import DONE
from doosra.gcp.managers.exceptions import *
from doosra.models.gcp_models import GcpAddress, GcpBackendService, GcpFirewallRule, GcpForwardingRule, GcpHealthCheck, \
    GcpInstance, GcpInstanceGroup, GcpSubnet, GcpTargetProxy, GcpVpcNetwork, GcpUrlMap
from .fetch_operations import FetchOperations


class ComputeEngineOperations(object):
    def __init__(self, cloud, credentials):
        self.cloud = cloud
        self.credentials = credentials
        self.service = discovery.build(COMPUTE_ENGINE_SERVICE_NAME, 'v1', credentials=self.credentials,
                                       cache_discovery=False)
        self.fetch_ops = FetchOperations(self.cloud, self.service)

    def push_obj_confs(self, obj, project_id, delete=False, update=False):
        if delete:
            func_map = {
                GcpAddress: self.delete_address,
                GcpFirewallRule: self.delete_firewall_rule,
                GcpVpcNetwork: self.delete_vpc_network,
                GcpSubnet: self.delete_subnet,
                GcpInstance: self.delete_instance,
                GcpInstanceGroup: self.delete_instance_group,
                GcpHealthCheck: self.delete_health_check,
                GcpBackendService: self.delete_backend_service,
                GcpForwardingRule: self.delete_forwarding_rule,
                GcpUrlMap: self.delete_url_map,
                GcpTargetProxy: self.delete_target_proxy
            }
        elif update:
            func_map = {
                GcpFirewallRule: self.update_firewall_rule,
                GcpVpcNetwork: self.patch_vpc_network,
                GcpSubnet: self.patch_subnet
            }
        else:
            func_map = {
                GcpFirewallRule: self.create_firewall_rule,
                GcpVpcNetwork: self.create_vpc_network,
                GcpSubnet: self.create_subnet,
                GcpAddress: self.create_address,
                GcpInstance: self.create_instance,
                GcpInstanceGroup: self.create_instance_group,
                GcpHealthCheck: self.create_health_check,
                GcpBackendService: self.create_backend_service,
                GcpForwardingRule: self.create_forwarding_rule,
                GcpUrlMap: self.create_url_map,
                GcpTargetProxy: self.create_target_proxy
            }

        func_map[obj.__class__](project_id, obj)

    def create_vpc_network(self, project_id, vpc_network_obj):
        """
        Create a new VPC network
        :param project_id:
        :param vpc_network_obj:
        :return:
        """
        request = self.service.networks().insert(project=project_id,
                                                 body=vpc_network_obj.to_json_body())
        self.execute(request, project_id)

    def patch_vpc_network(self, project_id, vpc_network_obj):
        """
        Update VPC network object
        :param project_id:
        :param vpc_network_obj:
        :return:
        """
        request = self.service.networks().patch(project=project_id, network=vpc_network_obj.name,
                                                body=vpc_network_obj.to_json_body(update=True))
        self.execute(request, project_id)

    def delete_vpc_network(self, project_id, vpc_network_obj):
        """
        Delete a VPC network
        :param project_id:
        :param vpc_network_obj:
        :return:
        """
        request = self.service.networks().delete(project=project_id, network=vpc_network_obj.name)
        self.execute(request, project_id)

    def create_subnet(self, project_id, subnet_obj):
        """
        Deploy the given subnet in the region specified
        :param project_id:
        :param subnet_obj:
        :return:
        """
        request = self.service.subnetworks().insert(project=project_id, region=subnet_obj.region,
                                                    body=subnet_obj.to_json_body())
        self.execute(request, project_id)

    def patch_subnet(self, project_id, subnet_obj):
        """
        Update VPC subnet object
        :param project_id: Project ID for this request
        :param subnet_obj: subnet obj to update to GCP
        :return:
        """
        fingerprint = self.fetch_ops.get_vpc_subnet_fingerprint(project_id, region=subnet_obj.region,
                                                                subnet=subnet_obj.name)
        subnet_json = subnet_obj.to_json_body(update=True)
        subnet_json['fingerprint'] = fingerprint
        request = self.service.subnetworks().patch(project=project_id, region=subnet_obj.region,
                                                   subnetwork=subnet_obj.name, body=subnet_json)
        self.execute(request, project_id)

    def delete_subnet(self, project_id, subnet_obj):
        """
        Delete the subnet in the region specified
        :param project_id:
        :param subnet_obj:
        :return:
        """
        request = self.service.subnetworks().delete(project=project_id,
                                                    region=subnet_obj.region,
                                                    subnetwork=subnet_obj.name)
        self.execute(request, project_id)

    def create_address(self, project_id, addr_obj):
        """
        Creates an address resource in the specified project using the data included in the request.
        :return:
        """
        if addr_obj.region:
            request = self.service.addresses().insert(project=project_id, region=addr_obj.region,
                                                      body=addr_obj.to_json_body())
        else:
            request = self.service.globalAddresses().insert(project=project_id,
                                                            body=addr_obj.to_json_body())
        self.execute(request, project_id)

    def delete_address(self, project_id, addr_obj):
        """
        Deletes an address resource in the specified project using the data included in the request.
        :return:
        """
        if addr_obj.region:
            request = self.service.addresses().delete(project=project_id, region=addr_obj.region,
                                                      address=addr_obj.name)
        else:
            request = self.service.globalAddresses().delete(project=project_id,
                                                            address=addr_obj.name)
        self.execute(request, project_id)

    def create_instance(self, project_id, gcp_instance_obj):
        """
        Create a new Instance
        :return: None
        """
        request = self.service.instances().insert(project=project_id, zone=gcp_instance_obj.zone,
                                                  body=gcp_instance_obj.to_json_body())
        self.execute(request, project_id)

    def delete_instance(self, project_id, instance_obj):
        """
        Delete an Instance
        :return:
        """
        request = self.service.instances().delete(project=project_id, instance=instance_obj.name,
                                                  zone=instance_obj.zone)
        self.execute(request, project_id)

    def create_firewall_rule(self, project_id, firewall_rule_obj):
        """
        Creates a firewall rule in the specified project using the data included in the request.
        :param project_id: Project ID for this request.
        :param firewall_rule_obj:
        :return:
        """
        request = self.service.firewalls().insert(project=project_id, body=firewall_rule_obj.to_json_body())
        self.execute(request, project_id)

    def update_firewall_rule(self, project_id, firewall_rule_obj):
        """
        Update a firewall rule in the specified project using the data included in the request.
        :param project_id: project ID for this request
        :param firewall_rule_obj:
        :return:
        """
        request = self.service.firewalls().patch(project=project_id, firewall=firewall_rule_obj.name,
                                                 body=firewall_rule_obj.to_json_body(update=True))
        self.execute(request, project_id)

    def delete_firewall_rule(self, project_id, firewall_rule_obj):
        """
        Delete a firewall rule in the specified project using the data included in the request.
        :param project_id: Project ID for this request.
        :param firewall_rule_obj:
        :return:
        """
        request = self.service.firewalls().delete(project=project_id, firewall=firewall_rule_obj.name)
        self.execute(request, project_id)

    def create_instance_group(self, project_id, instance_group_obj):
        """
        Create Instance Group. Load Balancing uses instance groups to organize instances
        :return:
        """
        request = self.service.instanceGroups().insert(project=project_id, zone=instance_group_obj.zone,
                                                       body=instance_group_obj.to_json_body())
        self.execute(request, project_id)

        if instance_group_obj.instances.all():
            self.add_instances_to_instance_group(project_id, instance_group_obj)

    def delete_instance_group(self, project_id, instance_group_obj):
        """
        Delete Instance group in GCP. Load Balancing uses instance groups to organize instances
        :return:
        """
        request = self.service.instanceGroups().delete(project=project_id, zone=instance_group_obj.zone,
                                                       instanceGroup=instance_group_obj.name)
        self.execute(request, project_id)

    def add_instances_to_instance_group(self, project_id, instance_group_obj):
        """
        Add instances to instance group in GCP
        """
        request = self.service.instanceGroups().addInstances(project=project_id, zone=instance_group_obj.zone,
                                                             instanceGroup=instance_group_obj.name,
                                                             body=instance_group_obj.to_json_body())
        self.execute(request, project_id)

    def remove_instances_from_instance_group(self, project_id, instance_group_obj):
        """
        Removes one or more instances from the specified instance group, but does not delete those instances.
        """
        request = self.service.instanceGroups().removeInstances(project=project_id, zone=instance_group_obj.zone,
                                                                instanceGroup=instance_group_obj.name,
                                                                body=instance_group_obj.to_json_body())
        self.execute(request, project_id)

    def create_health_check(self, project_id, health_check_obj):
        """
        Create health check resource
        :return:
        """
        request = self.service.healthChecks().insert(project=project_id, body=health_check_obj.to_json_body())
        self.execute(request, project_id)

    def delete_health_check(self, project_id, health_check_obj):
        """
        Delete health check resource
        :return:
        """
        request = self.service.healthChecks().delete(project=project_id, healthCheck=health_check_obj.name)
        self.execute(request, project_id)

    def create_backend_service(self, project_id, backend_service_obj):
        """
        Create backend service
        :return:
        """
        request = self.service.backendServices().insert(project=project_id, body=backend_service_obj.to_json_body())
        self.execute(request, project_id)

    def delete_backend_service(self, project_id, backend_service_obj):
        """
        Delete backend service
        :return:
        """
        request = self.service.backendServices().delete(project=project_id, backendService=backend_service_obj.name)
        self.execute(request, project_id)

    def create_forwarding_rule(self, project_id, forwarding_rule_obj):
        """
        Create forwarding rule
        :return:
        """
        request = self.service.globalForwardingRules().insert(project=project_id,
                                                              body=forwarding_rule_obj.to_json_body())
        self.execute(request, project_id)

    def delete_forwarding_rule(self, project_id, forwarding_rule_obj):
        """
        Delete forwarding rule
        :return:
        """
        request = self.service.globalForwardingRules().delete(project=project_id,
                                                              forwardingRule=forwarding_rule_obj.name)
        self.execute(request, project_id)

    def create_url_map(self, project_id, url_map_obj):
        """
        Create URL map
        :return:
        """
        request = self.service.urlMaps().insert(project=project_id, body=url_map_obj.to_json_body())
        self.execute(request, project_id)

    def delete_url_map(self, project_id, url_map_obj):
        """
        Delete URL Map
        :return:
        """
        request = self.service.urlMaps().delete(project=project_id, urlMap=url_map_obj.name)
        self.execute(request, project_id)

    def create_target_proxy(self, project_id, target_proxy_obj, type="HTTP"):
        """
        Create Target Proxy
        :return:
        """
        if type == "HTTP":
            request = self.service.targetHttpProxies().insert(project=project_id, body=target_proxy_obj.to_json_body())
            self.execute(request, project_id)

    def delete_target_proxy(self, project_id, target_proxy_obj, type="HTTP"):
        """
        Delete Target Proxy
        :return:
        """
        if type == "HTTP":
            request = self.service.targetHttpProxies().delete(project=project_id, targetHttpProxy=target_proxy_obj.name)
            self.execute(request, project_id)

    def wait_for_operation(self, project, operation, region=None, zone=None):
        while True:
            if zone:
                zone_name = zone.split("/")
                result = self.service.zoneOperations().get(
                    project=project,
                    zone=zone_name[-1],
                    operation=operation).execute()
            elif region:
                region_name = region.split("/")
                result = self.service.regionOperations().get(
                    project=project,
                    region=region_name[-1],
                    operation=operation).execute()
            else:
                result = self.service.globalOperations().get(
                    project=project,
                    operation=operation).execute()

            if result['status'] == DONE:
                if 'error' in result:
                    for error in result['error']['errors']:
                        raise CloudExecuteError(error.get('message'))
                return result

            time.sleep(2)

    def execute(self, request, project_id):
        """
        Executes request object on GCP cloud account and returns the response.
        :param request: request object
        :param project_id:
        :return:
        """
        try:
            response = request.execute()
            self.wait_for_operation(project_id, response.get("name"), response.get('region'), response.get('zone'))
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
