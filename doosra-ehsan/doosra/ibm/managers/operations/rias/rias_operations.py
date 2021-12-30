import time

import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, ReadTimeout, RequestException
from urllib3.exceptions import MaxRetryError, ReadTimeoutError
from urllib3.util.retry import Retry
from doosra import db as doosradb

from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.operations.rias.consts import *
from doosra.models import IBMAddressPrefix, IBMCredentials, IBMFloatingIP, IBMInstance, IBMLoadBalancer, IBMNetworkAcl, \
    IBMNetworkAclRule, IBMPublicGateway, IBMNetworkInterface, IBMSecurityGroup, IBMSecurityGroupRule, IBMSshKey, \
    IBMSubnet, IBMVpcNetwork, IBMVpnGateway, IBMImage, IBMVpcRoute, IBMIPSecPolicy, IBMIKEPolicy, IBMVpnConnection, \
    KubernetesCluster, KubernetesClusterWorkerPool, IBMServiceCredentials
from .fetch_operations import FetchOperations
from .rias_patterns import *
from .raw_fetch_operations import RawFetchOperations


class RIASOperations(object):
    def __init__(self, cloud, region, iam_ops, resource_ops):
        self.cloud = cloud
        self.resource_ops = resource_ops
        self.iam_ops = iam_ops
        self.region = region or DEFAULT_REGION
        self.base_url = RIAS_BASE_URL.format(region=self.region)
        self.k8s_base_url = KUBERNETES_CLUSTER_BASE_URL
        self.session_k8s = self.requests_retry_session(retries=30, k8s=True)
        self.session = self.requests_retry_session()
        self.fetch_ops = FetchOperations(self.cloud, self.region, self.base_url, self.session, self.iam_ops,
                                         self.resource_ops, self.k8s_base_url, self.session_k8s)
        self.raw_fetch_ops = RawFetchOperations(self.cloud, self.region, self.base_url, self.session, self.iam_ops,
                                                self.resource_ops, self.k8s_base_url, self.session_k8s)

    def push_obj_confs(self, obj, delete=False, update=False):
        if delete:
            func_map = {
                IBMAddressPrefix: self.delete_address_prefix,
                IBMNetworkAcl: self.delete_network_acl,
                IBMNetworkAclRule: self.delete_network_acl_rule,
                IBMPublicGateway: self.delete_public_gateway,
                IBMVpnGateway: self.delete_vpn_gateway,
                IBMVpcRoute: self.delete_vpc_route,
                IBMVpcNetwork: self.delete_vpc,
                IBMSubnet: self.delete_subnet,
                IBMSecurityGroup: self.delete_security_group,
                IBMSecurityGroupRule: self.delete_security_group_rule,
                IBMInstance: self.delete_instance,
                IBMFloatingIP: self.delete_floating_ip,
                IBMSshKey: self.delete_ssh_key,
                IBMLoadBalancer: self.delete_load_balancer,
                IBMIPSecPolicy: self.delete_ipsec_policy,
                IBMIKEPolicy: self.delete_ike_policy,
                IBMVpnConnection: self.delete_vpn_connection}

        elif update:
            func_map = {
                IBMSubnet: self.attach_public_gateway_to_subnet,
                IBMNetworkInterface: self.reserve_floating_ip_for_interface}

        else:
            func_map = {
                IBMAddressPrefix: self.create_address_prefix,
                IBMNetworkAcl: self.create_network_acl,
                IBMNetworkAclRule: self.create_network_acl_rule,
                IBMPublicGateway: self.create_public_gateway,
                IBMVpnGateway: self.create_vpn_gateway,
                IBMVpcNetwork: self.create_new_vpc,
                IBMVpcRoute: self.create_ibm_vpc_route,
                IBMSubnet: self.create_subnet,
                IBMSecurityGroup: self.create_security_group,
                IBMSecurityGroupRule: self.create_security_group_rule,
                IBMInstance: self.create_instance,
                IBMFloatingIP: self.create_floating_ip,
                IBMSshKey: self.create_ssh_key,
                IBMLoadBalancer: self.create_load_balancer,
                IBMIKEPolicy: self.create_ike_policy,
                IBMImage: self.create_image,
                IBMIPSecPolicy: self.create_ipsec_policy,
                IBMVpnConnection: self.create_vpn_connection,
                KubernetesCluster: self.create_ibm_k8s_cluster,
                KubernetesClusterWorkerPool: self.create_ibm_k8s_worker_pool}

        if obj.__class__.__name__ == IBMVpnConnection.__name__:
            func_map[obj.__class__](obj, obj.ibm_vpn_gateway)
        else:
            func_map[obj.__class__](obj)

    def fetch_obj_status_method_mapper(self, obj):
        func_map = {
            IBMVpcNetwork: self.fetch_ops.get_vpc_status,
            IBMVpcRoute: self.fetch_ops.get_vpc_route_status,
            IBMSubnet: self.fetch_ops.get_subnet_status,
            IBMPublicGateway: self.fetch_ops.get_public_gateway_status,
            IBMVpnGateway: self.fetch_ops.get_vpn_gateway_status,
            IBMInstance: self.fetch_ops.get_instance_status,
            IBMLoadBalancer: self.fetch_ops.get_load_balancer_status,
            IBMImage: self.fetch_ops.get_image_status,
            IBMFloatingIP: self.fetch_ops.get_floating_ip_status,
            KubernetesCluster: self.fetch_ops.get_k8s_cluster_status,
            KubernetesClusterWorkerPool: self.get_k8s_workerpool_workers_status
        }

        if func_map.get(obj.__class__):
            return func_map[obj.__class__]

    def create_new_vpc(self, vpc_obj):
        """
        This request creates a new VPC from a VPC template.
        :return:
        """
        response = self.execute(vpc_obj, self.format_api_url(CREATE_VPC_PATTERN), data=vpc_obj.to_json_body())
        return response

    def delete_vpc(self, vpc_obj):
        """
        This request deletes a VPC.
        :return:
        """
        response = self.execute(vpc_obj, self.format_api_url(DELETE_VPC_PATTERN, vpc_id=vpc_obj.resource_id))
        return response

    def create_ibm_vpc_route(self, vpc_route_obj):
        """
        This request creates a new Route for the the VPC from Route Template.
        :param vpc_id:
        :param vpc_route_obj:
        :return:
        """
        response = self.execute(vpc_route_obj,
                                self.format_api_url(CREATE_VPC_ROUTE_PATTERN,
                                                    vpc_id=vpc_route_obj.ibm_vpc_network.resource_id),
                                data=vpc_route_obj.to_json_body())
        return response

    def delete_vpc_route(self, vpc_route_obj):
        """
        This request deletes a VPC Route.
        :return:
        """
        response = self.execute(vpc_route_obj, self.format_api_url(DELETE_VPC_ROUTE_PATTERN,
                                                                   vpc_id=vpc_route_obj.ibm_vpc_network.resource_id,
                                                                   route_id=vpc_route_obj.resource_id))
        return response

    def create_floating_ip(self, floating_ip_obj):
        """
        This request creates a new floating ip from a Floating IP template.
        :return:
        """
        response = self.execute(floating_ip_obj, self.format_api_url(CREATE_FLOATING_IP_PATTERN),
                                data=floating_ip_obj.to_json_body())
        return response

    def delete_floating_ip(self, floating_ip_obj):
        """
        This request deletes a Floating IP obj.
        :return:
        """
        response = self.execute(floating_ip_obj, self.format_api_url(
            DELETE_FLOATING_IP_PATTERN, floating_ip_id=floating_ip_obj.resource_id))
        return response

    def create_subnet(self, subnet_obj):
        """
        This request creates a new VPC from a VPC template.
        :return:
        """
        response = self.execute(subnet_obj, self.format_api_url(CREATE_SUBNET_PATTERN), data=subnet_obj.to_json_body())
        return response

    def delete_subnet(self, subnet_obj):
        """
        This request deletes a subnet within a VPC.
        :return:
        """
        response = self.execute(
            subnet_obj, self.format_api_url(DELETE_SUBNET_PATTERN, subnet_id=subnet_obj.resource_id))
        return response

    def create_network_acl(self, network_acl_obj):
        """
        This request creates a new network ACL from a network ACL template.
        :return:
        """
        response = self.execute(
            network_acl_obj, self.format_api_url(CREATE_ACL_PATTERN), data=network_acl_obj.to_json_body())
        return response

    def delete_network_acl(self, network_acl_obj):
        """
        This request deletes a Network ACL.
        :return:
        """
        response = self.execute(
            network_acl_obj, self.format_api_url(DELETE_ACL_PATTERN, acl_id=network_acl_obj.resource_id))
        return response

    def create_network_acl_rule(self, network_acl_rule_obj):
        """
        This request creates a new network ACL Rule from a network ACL template.
        :return:
        """
        response = self.execute(
            network_acl_rule_obj,
            self.format_api_url(CREATE_ACL_RULE_PATTERN, acl_id=network_acl_rule_obj.ibm_network_acl.resource_id),
            data=network_acl_rule_obj.to_json_body())
        return response

    def delete_network_acl_rule(self, network_acl_rule_obj, acl_id):
        """
        This request deletes a Network ACL rule.
        :return:
        """
        response = self.execute(
            network_acl_rule_obj,
            self.format_api_url(DELETE_ACL_RULE_PATTERN, acl_id=acl_id,
                                rule_id=network_acl_rule_obj.resource_id))
        return response

    def delete_volume(self, volume):
        """
              This request deletes a Volume.
              :return:
              """
        response = self.execute(
            volume, self.format_api_url(DELETE_VOLUME_PATTERN, volume_id=volume.resource_id)
        )
        return response

    def attach_acl_to_subnet(self, subnet_obj):
        """
        This request attaches the network ACL, specified in the request body
        :return:
        """
        response = self.execute(
            subnet_obj, self.format_api_url(ATTACH_ACL_TO_SUBNET_PATTERN, subnet_id=subnet_obj.resource_id),
            data={"id": subnet_obj.network_acl.resource_id if subnet_obj.network_acl else None})
        return response

    def create_security_group(self, security_group_obj):
        """
        This request creates a new security group from a security group template
        :return:
        """
        response = self.execute(
            security_group_obj, self.format_api_url(CREATE_SECURITY_GROUP_PATTERN),
            data=security_group_obj.to_json_body())
        return response

    def create_security_group_rule(self, rule_obj):
        """
        This request creates a new Security Group Rule on IBM Cloud.
        :return:
        """
        response = self.execute(
            rule_obj, self.format_api_url(CREATE_SECURITY_GROUP_RULE_PATTERN,
                                          security_group_id=rule_obj.security_group.resource_id),
            data=rule_obj.to_json_body())
        return response

    def delete_security_group(self, security_group_obj):
        """
        This request deletes a Security Group.
        :return:
        """
        response = self.execute(
            security_group_obj, self.format_api_url(
                DELETE_SECURITY_GROUP_PATTERN, security_group_id=security_group_obj.resource_id))
        return response

    def detach_network_interface_from_security_group(self, ibm_security_group, network_interface):
        """
        this request remove a network interface from security group
        @param network_interface:
        @param ibm_security_group:
        @return:
        """
        response = self.execute(
            ibm_security_group,
            self.format_api_url(
                DETACH_NETWORK_INTERFACE_FROM_SECURITY_GROUP_PATTERN, security_group_id=ibm_security_group.resource_id,
                network_interface_id=network_interface.resource_id))
        return response

    def delete_security_group_rule(self, security_group_rule_obj, security_group_id):
        """
        This request deletes a IBM security group rule.
        :return:
        """
        response = self.execute(
            security_group_rule_obj,
            self.format_api_url(DELETE_SECURITY_GROUP_RULE_PATTERN,
                                security_group_id=security_group_id,
                                rule_id=security_group_rule_obj.resource_id))
        return response

    def create_public_gateway(self, public_gateway_obj):
        """
        This request creates a new public gateway from a public gateway template
        :return:
        """
        response = self.execute(
            public_gateway_obj, self.format_api_url(CREATE_PUBLIC_GATEWAY_PATTERN),
            data=public_gateway_obj.to_json_body())
        return response

    def delete_public_gateway(self, public_gateway_obj):
        """
        This request deletes a Public Gateway.
        :return:
        """
        response = self.execute(
            public_gateway_obj, self.format_api_url(
                DELETE_PUBLIC_GATEWAY_PATTERN, public_gateway_id=public_gateway_obj.resource_id))
        return response

    def create_instance(self, instance_obj):
        """
        This request creates a new instance from a instance template
        :return:
        """
        response = self.execute(
            instance_obj, self.format_api_url(CREATE_INSTANCE_PATTERN), data=instance_obj.to_json_body())
        return response

    def delete_instance(self, instance_obj):
        """
        This request deletes an Instance.
        :return:
        """

        response = self.execute(
            instance_obj, self.format_api_url(DELETE_INSTANCE_PATTERN, instance_id=instance_obj.resource_id))
        return response

    def stop_instance(self, instance_obj):
        """
        This request creates a new action which will be queued up to run as soon as any pending or
        running actions have completed
        :return:
        """
        response = self.execute(
            instance_obj, self.format_api_url(CREATE_INSTANCE_ACTION_PATTERN, instance_id=instance_obj.resource_id),
            data={"type": "stop"}, required_status="stopped")

        return response

    def create_ssh_key(self, ssh_key_obj):
        """
        This request creates a new ssh key from a ssh key template
        :return:
        """
        response = self.execute(
            ssh_key_obj, self.format_api_url(CREATE_SSH_KEY_PATTERN), data=ssh_key_obj.to_json_body())
        return response

    def delete_ssh_key(self, ssh_key_obj):
        """
        This request deletes a SSH Key
        :return:
        """
        response = self.execute(
            ssh_key_obj, self.format_api_url(DELETE_SSH_KEY_PATTERN, ssh_key_id=ssh_key_obj.resource_id))
        return response

    def create_image(self, image_obj):
        """
        This request creates a new image from a image template
        :return:
        """
        response = self.execute(
            image_obj, self.format_api_url(CREATE_IMAGE), data=image_obj.to_json_body())
        return response

    def delete_image(self, image_obj):
        """
        This request deletes an image.
        :return:
        """
        response = self.execute(
            image_obj, self.format_api_url(DELETE_IMAGE, image_id=image_obj.resource_id))
        return response

    def attach_public_gateway_to_subnet(self, subnet_obj):
        """
        This request attaches the Public Gateway, specified in the request body
        :return:
        """
        response = self.execute(
            subnet_obj, self.format_api_url(ATTACH_PUBLIC_GATEWAY_TO_SUBNET_PATTERN, subnet_id=subnet_obj.resource_id),
            data={"id": subnet_obj.ibm_public_gateway.resource_id if subnet_obj.ibm_public_gateway else None})
        return response

    def add_local_cidrs_connection(self, gateway_resource_id, connection_obj, prefix,
                                                           prefix_length):
        """
        This request updates the specified VPN Connection's Local CIDR
        :return:
        """
        response = self.execute(
            connection_obj,
            self.format_api_url(UPDATE_LOCAL_CIDR_VPN_CONNECTION, vpn_gateway_id=gateway_resource_id,
                                id=connection_obj.resource_id, prefix_address=prefix, prefix_length=prefix_length
        ))
        return response

    def add_peer_cidrs_connection(self, gateway_resource_id, connection_obj, prefix,
                                                           prefix_length):
        """
        This request updates the specified VPN Connection's Peer CIDR
        :return:
        """
        response = self.execute(
            connection_obj,
            self.format_api_url(UPDATE_PEER_CIDR_VPN_CONNECTION, vpn_gateway_id=gateway_resource_id,
                                id=connection_obj.resource_id, prefix_address=prefix,
                                prefix_length=prefix_length
            ))
        return response

    def delete_local_cidrs_connection(self, gateway_resource_id, connection_obj, prefix,
                                                           prefix_length):
        """
        This request DELETE the specified VPN Connection's Local CIDR
        :return:
        """
        response = self.execute(
            connection_obj,
            self.format_api_url(DELETE_VPN_LOCAL_CIDR_PATTERN, vpn_gateway_id=gateway_resource_id,
                                id=connection_obj.resource_id, prefix_address=prefix, prefix_length=prefix_length
        ))
        return response

    def delete_peer_cidrs_connection(self, gateway_resource_id, connection_obj, prefix,
                                                           prefix_length):
        """
        This request DELETE the specified VPN Connection's Peer CIDR
        :return:
        """
        response = self.execute(
            connection_obj,
            self.format_api_url(DELETE_VPN_PEER_CIDR_PATTERN, vpn_gateway_id=gateway_resource_id,
                                id=connection_obj.resource_id, prefix_address=prefix,
                                prefix_length=prefix_length
            ))
        return response

    def detach_public_gateway_to_subnet(self, subnet_obj):
        """
        This request attaches the Public Gateway, specified in the request body
        :return:
        """
        response = self.execute(
            subnet_obj, self.format_api_url(DETACH_PUBLIC_GATEWAY_TO_SUBNET_PATTERN, subnet_id=subnet_obj.resource_id))
        return response

    def create_ike_policy(self, ike_policy_obj):
        """
        This request creates a new IKE Policy from a IKE Policy template
        :return:
        """
        response = self.execute(
            ike_policy_obj, self.format_api_url(CREATE_IKE_POLICY),
            data=ike_policy_obj.to_json_body())
        return response

    def delete_ike_policy(self, ike_policy_obj):
        """
        This request deletes a IKE Policy.
        :return:
        """
        response = self.execute(
            ike_policy_obj, self.format_api_url(DELETE_IKE_POLICY, ike_policy_id=ike_policy_obj.resource_id))
        return response

    def create_ipsec_policy(self, ipsec_policy_obj):
        """
        This request creates a new IKE Policy from a IKE Policy template
        :return:
        """
        response = self.execute(
            ipsec_policy_obj, self.format_api_url(CREATE_IPSEC_POLICY),
            data=ipsec_policy_obj.to_json_body())
        return response

    def delete_ipsec_policy(self, ipsec_policy_obj):
        """
        This request deletes a IPSec Policy.
        :return:
        """
        response = self.execute(
            ipsec_policy_obj, self.format_api_url(DELETE_IPSEC_POLICY, ipsec_policy_id=ipsec_policy_obj.resource_id))
        return response

    def create_vpn_gateway(self, vpn_gateway_obj):
        """
        This request creates a new VPN gateway from a VPN gateway template
        :return:
        """
        response = self.execute(
            vpn_gateway_obj, self.format_api_url(CREATE_VPN_GATEWAY_PATTERN),
            data=vpn_gateway_obj.to_json_body())
        return response

    def delete_vpn_gateway(self, vpn_gateway_obj):
        """
        This request deletes a VPN Gateway.
        :return:
        """
        response = self.execute(
            vpn_gateway_obj, self.format_api_url(DELETE_VPN_GATEWAY, vpn_gateway_id=vpn_gateway_obj.resource_id))
        return response

    def create_vpn_connection(self, connection_obj, vpn_gateway_obj):
        """
        This request creates a VPN Connection for a Specific VPN Gateway.
        :param connection_obj:
        :param vpn_gateway_obj:

        :return:
        """
        response = self.execute(
            connection_obj,
            self.format_api_url(CREATE_VPN_CONNECTION, vpn_gateway_id=vpn_gateway_obj.resource_id),
            data=connection_obj.to_json_body())

        return response

    def delete_vpn_connection(self, vpn_connection_obj, vpn_gateway_id):
        """
        This request deletes a IKE Policy.
        :return:
        """
        response = self.execute(
            vpn_connection_obj,
            vpn_gateway_id,
            self.format_api_url(DELETE_VPN_CONNECTION, vpn_gateway_id=vpn_gateway_id,
                                connection_id=vpn_connection_obj.resource_id))
        return response

    def reserve_floating_ip_for_interface(self, network_interface_obj):
        """
        This request associates the specified floating IP with the specified network interface
        :param network_interface_obj:
        :return:
        """
        response = self.execute(
            network_interface_obj,
            self.format_api_url(ATTACH_FLOATING_IP_TO_INTERFACE_PATTERN,
                                instance_id=network_interface_obj.ibm_instance.resource_id,
                                network_interface_id=network_interface_obj.resource_id,
                                floating_ip_id=network_interface_obj.floating_ip.resource_id))
        return response

    def detach_floating_ip_for_interface(self, network_interface_obj):
        """
        This request removes the specified floating IP with the specified network interface
        :param network_interface_obj:
        :return:
        """
        response = self.execute(
            network_interface_obj,
            self.format_api_url(DETACH_FLOATING_IP_TO_INTERFACE_PATTERN,
                                instance_id=network_interface_obj.ibm_instance.resource_id,
                                network_interface_id=network_interface_obj.resource_id,
                                floating_ip_id=network_interface_obj.floating_ip.resource_id))
        return response

    def delete_network_interface(self, instance_id, network_interface_id):
        """
        This request removes the specified floating IP with the specified network interface
        :param network_interface_id:
        :param instance_id:

        :return:
        """
        response = self.execute(
            instance_id,
            network_interface_id,
            self.format_api_url(DETACH_FLOATING_IP_TO_INTERFACE_PATTERN,
                                instance_id=instance_id,
                                network_interface_id=network_interface_id))
        return response

    def delete_load_balancer_listener(self, load_balancer, listener):
        """
        This request removes a single listener
        """
        response = self.execute(load_balancer, self.format_api_url(
            DELETE_LOAD_BALANCER_LISTENER_PATTERN, listener_id=listener.resource_id,
            load_balancer_id=load_balancer.resource_id))
        return response

    def create_load_balancer(self, ibm_load_balancer):
        """
        This request removes the specified load balancer with the specified load balancer object
        :return:
        """
        response = self.execute(
            ibm_load_balancer, self.format_api_url(CREATE_LOAD_BALANCER_PATTERN), data=ibm_load_balancer.to_json_body())
        return response
    

    def create_ibm_k8s_cluster(self, k8s_cluster):
        """
        This request create the specified k8s cluster with the specified k8s cluster object
        :return:
        """
        data = k8s_cluster.to_json_body(managed_view="true")
        if data['type'] == "openshift":
            cos_instance_crn = doosradb.session.query(IBMServiceCredentials).filter_by(cloud_id=self.cloud.id).first()
            data['cosInstanceCRN'] = cos_instance_crn.resource_instance_id
        data['workerPool'].update({'vpcID': k8s_cluster.ibm_vpc_network.resource_id})
        json_cluster = k8s_cluster.to_json()
        json_worker_pools = json_cluster["worker_pools"]
        if len(json_worker_pools) < 2:
            response = self.execute_(
                k8s_cluster,
                self.format_api_url(CREATE_K8S_CLUSTER_PATTERN),
                data=data, required_status="normal")
            k8s_cluster.resource_id = response['clusterID']
            worker_pool_response = self.fetch_ops.execute_(
                self.fetch_ops.format_api_url(GET_K8S_CLUSTERS_WORKER_POOL, cluster=response['clusterID'])
            )
            worker_pool_name = ""
            worker_pool_id = ""
            for worker_pool in worker_pool_response:
                worker_pool_name = worker_pool['poolName']
                worker_pool_id = worker_pool['id']
            worker_pools = doosradb.session.query(KubernetesClusterWorkerPool).filter_by(kubernetes_cluster_id=k8s_cluster.id).all()
            for worker_pool in worker_pools:
                if worker_pool.name == worker_pool_name:
                    worker_pool.resource_id = worker_pool_id
            doosradb.session.commit()
        else:
            response = self.execute_(
                k8s_cluster,
                self.format_api_url(CREATE_K8S_CLUSTER_PATTERN),
                data=data, required_status="deploying")
            k8s_cluster.resource_id = response['clusterID']
            time.sleep(3)
            worker_pool_response = self.fetch_ops.execute_(
                self.fetch_ops.format_api_url(GET_K8S_CLUSTERS_WORKER_POOL, cluster=response['clusterID'])
            )
            worker_pool_name = ""
            worker_pool_id = ""
            for worker_pool in worker_pool_response:
                worker_pool_name = worker_pool['poolName']
                worker_pool_id = worker_pool['id']
            worker_pools = doosradb.session.query(KubernetesClusterWorkerPool).filter_by(kubernetes_cluster_id=k8s_cluster.id).all()
            for worker_pool in worker_pools:
                if worker_pool.name == worker_pool_name:
                    worker_pool.resource_id = worker_pool_id
            doosradb.session.commit()

            workerpools_to_create = list()
            for doosra_k8s_workerpool in k8s_cluster.worker_pools:
                if doosra_k8s_workerpool.name != worker_pool_name:
                    workerpools_to_create.append(doosra_k8s_workerpool)
            self.create_ibm_multiple_worker_pools(workerpools_to_create)
            self.wait_for_operation(k8s_cluster, response['clusterID'], required_status="normal", time_to_sleep=4)

        return response

    def create_ibm_k8s_worker_pool(self, k8s_workerpool):
        """
        This request create the specified k8s cluster's Workerpool with the specified workerpool object
        :return:
        """
        data = k8s_workerpool.to_json_body()
        data['cluster'] = k8s_workerpool.ibm_k8kubernetes_clusterss_clusters.resource_id
        data['vpcID'] = k8s_workerpool.kubernetes_clusters.ibm_vpc_network.resource_id
        response = self.execute_(
            k8s_workerpool,
            self.format_api_url(CREATE_K8S_WORKERPOOL_PATTERN),
            data=data, required_status="deployed"
        )

        return response

    def create_ibm_multiple_worker_pools(self, k8s_workerpools):
        """
        This request create multiple k8s cluster Workerpools with the specified workerpool objects
        :return:
        """
        workerpools_to_delete = list()
        for k8s_workerpool in k8s_workerpools:
            data = k8s_workerpool.to_json_body()
            data['cluster'] = k8s_workerpool.kubernetes_clusters.resource_id
            data['vpcID'] = k8s_workerpool.kubernetes_clusters.ibm_vpc_network.resource_id

            try:
                response = self.execute_(
                    k8s_workerpool,
                    self.format_api_url(CREATE_K8S_WORKERPOOL_PATTERN),
                    data=data, required_status="provisioning"
                )
                self.set_workerpool_resource(workerpool_id=k8s_workerpool.id, resource_id=response["workerPoolID"])

            except(IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError, Exception) as ex:
                current_app.logger.info("Wokerpool of name '{}' got Exception: ".format(k8s_workerpool.name))
                current_app.logger.info(ex)
                workerpools_to_delete.append(k8s_workerpool)

        if workerpools_to_delete:
            for index in range(len(workerpools_to_delete)):
                doosradb.session.delete(workerpools_to_delete[index])

        doosradb.session.commit()


    def set_workerpool_resource(self, workerpool_id, resource_id):
        """
        This request set the resource_id for specified workerpool
        :return:
        """
        worker_pool = doosradb.session.query(KubernetesClusterWorkerPool).filter_by(id=workerpool_id).first()
        worker_pool.resource_id = resource_id
        doosradb.session.commit()


    def get_k8s_workerpool_workers_status(self, workerpool_id, doosra_cluster_id):
        """
        This request retrieves workerpool's all workers and checks it's deployed state  a single k8s cluster specified by the identifier in the URL.
        :return:
        """
        ibm_k8s_cluster = doosradb.session.query(KubernetesCluster).filter_by(id=doosra_cluster_id).first()
        workers = self.fetch_ops.execute_(
            self.fetch_ops.format_api_url(
                GET_K8S_WORKERPOOL_WORKERS,
                cluster=ibm_k8s_cluster.resource_id,
                workerpool=workerpool_id,
                showDeleted=False
            )
        )
        isDeployed = False
        for worker in workers:
            if worker["lifecycle"]["actualState"] == "deployed":
                isDeployed = True
            else:
                isDeployed = False
                break

        if not isDeployed:
            return "provisioning"
        return "deployed"


    def delete_ibm_k8s_cluster(self, ibm_k8s_cluster):
        """
        This request removes the specified K8S Cluster with the specified k8s cluster id
        :return:
        """
        response = self.execute_(
            ibm_k8s_cluster, self.format_api_url(
                DELETE_K8S_CLUSTER_PATTERN, cluster=ibm_k8s_cluster.resource_id))
        return response

    def delete_load_balancer(self, ibm_load_balancer):
        """
        This request removes the specified load balancer with the specified load balancer id
        :return:
        """
        response = self.execute(
            ibm_load_balancer, self.format_api_url(
                DELETE_LOAD_BALANCER_PATTERN, load_balancer_id=ibm_load_balancer.resource_id))
        return response

    def create_address_prefix(self, address_prefix_obj):
        """
        This request creates address_prefix in VPC
        :return:
        """
        response = self.execute(
            address_prefix_obj,
            self.format_api_url(CREATE_ADDRESS_PREFIX_PATTERN, vpc_id=address_prefix_obj.ibm_vpc_network.resource_id),
            data=address_prefix_obj.to_json_body())
        return response

    def delete_address_prefix(self, address_prefix_obj, vpc_id):
        """
        This request removes the specified address prefix from VPC
        :return:
        """
        response = self.execute(
            address_prefix_obj, self.format_api_url(
                DELETE_ADDRESS_PREFIX_PATTERN, vpc_id=vpc_id,
                address_prefix_id=address_prefix_obj.resource_id))
        return response

    def delete_volume_attachment(self, ibm_instance, volume_attachment):
        """
        This request removes the volume attachment of instance
        :return:
        """
        response = self.execute(
            volume_attachment,
            self.format_api_url(
                DELETE_VOLUME_ATTACHMENT_PATTERN, instance_id=ibm_instance.resource_id,
                volume_attachment_id=volume_attachment.resource_id))
        return response

    @staticmethod
    def format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the unformatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def requests_retry_session(self, retries=5, k8s=None):
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 503, 504),
            method_whitelist=["GET", "PUT", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        if k8s:
            base_url = self.k8s_base_url
        else:
            base_url = self.base_url
        self.session.mount(base_url, adapter)
        return self.session

    def wait_for_operation(self, obj, resource_id, required_status=None, time_to_sleep=None):
        """
        Poll for the resource creation or deletion operation and do so while it is completed/deleted
        :return:
        """
        obj_fetch_conf = self.fetch_obj_status_method_mapper(obj)
        if obj_fetch_conf and not resource_id:
            return

        if obj_fetch_conf:
            while True:
                if time_to_sleep:
                    time.sleep(time_to_sleep)

                if hasattr(obj, "kubernetes_cluster_id"):
                    status = obj_fetch_conf(resource_id, obj.kubernetes_cluster_id)
                else:
                    status = obj_fetch_conf(resource_id)

                if not status:
                    break

                if required_status and required_status == status:
                    return True

                elif status == FAILED:
                    return

                elif status == AVAILABLE or status == ACTIVE or status == STABLE:
                    return True

                elif obj.__class__.__name__ == IBMInstance.__name__:
                    if status == RUNNING:
                        return True

                time.sleep(3)

        return True

    def execute(self, obj, request, data=None, required_status=None):
        """
        The following method executes the request on IBM Cloud and then polls for the resource creation or
        deletion operation and do so while it is completed/deleted.
        :return:
        """
        request_url = request[1].format(base_url=self.base_url, version=VERSION, generation=GENERATION)
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)

        try:
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(IBMCredentials(self.iam_ops.authenticate_cloud_account()))

            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.info("{0}: {1} {2}".format(request[0], request_url, data if data else ""))
            response = self.session.request(request[0], request_url, json=data, timeout=50, headers=headers)
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request_url)
        else:
            if response.status_code == 401:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code not in [200, 201, 202, 204, 404]:
                raise IBMExecuteError(response)

            status = self.wait_for_operation(obj, obj.resource_id or response.json().get("id"), required_status)
            if not status:
                raise IBMInvalidRequestError(
                    "The requested operation could not be performed:\n{0} : {1}".format(request[0], request_url))

            return response.json() if response.text else ""

    def execute_(self, obj, request, data=None, required_status=None):
        """
        The following method executes the request on IBM Cloud and then polls for the resource creation or
        deletion operation and do so while it is completed/deleted.
        :return:
        """
        request_url = request[1].format(k8s_base_url=self.k8s_base_url)
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)

        try:
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(IBMCredentials(self.iam_ops.authenticate_cloud_account()))

            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.info("{0}: {1} {2}".format(request[0], request_url, data if data else ""))
            if headers:
                if hasattr(obj, 'disk_encryption'):
                    headers.update({"Auth-Refresh-Token": self.cloud.credentials.refresh_token, "Auth-Resource-Group": obj.kubernetes_clusters.ibm_resource_group.name})
                else:
                    headers.update({"Auth-Refresh-Token": self.cloud.credentials.refresh_token, "Auth-Resource-Group": obj.ibm_resource_group.name})
            response = self.session_k8s.request(request[0], request_url, json=data, timeout=50, headers=headers)
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request_url)
        else:
            if response.status_code == 401:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code not in [200, 201, 202, 204, 404]:
                raise IBMExecuteError(response.json())
            time.sleep(60)
            status = self.wait_for_operation(obj, obj.resource_id or response.json().get("clusterID") or response.json().get("workerPoolID"), required_status)
            if not status:
                raise IBMInvalidRequestError(
                    "The requested operation could not be performed:\n{0} : {1}".format(request[0], request_url))

            return response.json() if response.text else ""
