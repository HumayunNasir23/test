"""
This file contains Client for K8S related APIs
"""
"""
This file contains Client for images related APIs
"""
import logging

import requests

from .paths import *
from ..base_client import BaseClient
from ..urls import KUBERNETES_CLUSTER_URL_TEMPLATE, CLASSIC_KUBERNETES_CLUSTERS_URL_TEMPLATE

LOGGER = logging.getLogger(__name__)


class K8sClient(BaseClient):
    """
    Client for K8S related APIs
    """

    def __init__(self, cloud_id):
        super(K8sClient, self).__init__(cloud_id)

    def get_all_locations(self):
        """
        :param none:
        :return: Lists all Locations available
        """
        request = requests.Request("GET", CLASSIC_KUBERNETES_CLUSTERS_URL_TEMPLATE.format(
            path=LIST_ALL_LOCATIONS))

        response = self._execute_request(request, "K8S_RESOURCE")

        return response

    def get_k8s_kube_versions(self):
        """
        :param none:
        :return: Lists Kubernetes and Openshift Kube Versions
        """
        request = requests.Request("GET", KUBERNETES_CLUSTER_URL_TEMPLATE.format(
            path=GET_K8S_KUBE_VERSIONS))
        response = self._execute_request(request, "K8S_RESOURCE")
        return response

    def list_k8s_zone_flavours(self, zone, provider):
        """
        :param zone: Availability zone in a region
        :return: Lists all Flavors available for cluster creation
        """
        request = requests.Request("GET", KUBERNETES_CLUSTER_URL_TEMPLATE.format(
            path=LIST_ZONE_FLAVORS_FOR_CLUSTER_CREATION.format(zone=zone, provider=provider)))

        response = self._execute_request(request, "K8S_RESOURCE")

        return response

    def list_k8s_cluster(self, provider):
        """
        :param provider: cluster region vpc-gen1/gen2 or ALL
        :return: Lists all K8S Clusters
        """

        if provider == "ALL":
            request = requests.Request("GET",
                                       KUBERNETES_CLUSTER_URL_TEMPLATE.format(path=LIST_ALL_K8S_CLUSTER_PATH))
        else:
            request = requests.Request("GET",
                                       KUBERNETES_CLUSTER_URL_TEMPLATE.format(path=LIST_K8S_CLUSTERS_PATH.format(
                                           provider=provider)))

        response = self._execute_request(request, "K8S_RESOURCE")
        return response

    def get_k8s_cluster_detail(self, region, resource_group, cluster):
        """
        :param region: cluster region
        :param resource_group: resource group of the cluster
        :param cluster: cluster id or name
        :return: K8S clusters details
        """

        request = requests.Request("GET",
                                   KUBERNETES_CLUSTER_URL_TEMPLATE.format(path=GET_K8S_CLUSTERS_DETAIL_PATH.format(
                                       cluster=cluster))
                                   )
        if request.headers:
            request.headers.update({"X-Region": region, "Auth-Resource-Group": resource_group})
        else:
            request.headers = {"X-Region": region, "Auth-Resource-Group": resource_group}

        response = self._execute_request(request, "K8S_RESOURCE")
        return response
    
    def get_k8s_cluster_worker_pool(self, region, resource_group, cluster):
        """
        :param region: cluster region
        :param resource_group: resource group of the cluster
        :param cluster: cluster id or name
        :return: K8S cluster's worker-pool
        """
    
        request = requests.Request("GET", KUBERNETES_CLUSTER_URL_TEMPLATE.format(
            path=GET_K8S_CLUSTERS_WORKER_POOL_PATH.format(cluster=cluster)))
        if request.headers:
            request.headers.update({"X-Region": region, "Auth-Resource-Group": resource_group})
        else:
            request.headers = {"X-Region": region, "Auth-Resource-Group": resource_group}
    
        response = self._execute_request(request, "K8S_RESOURCE")
        return response

    def get_k8s_cluster_kube_config(self, cluster, resource_group=None):
        """
        :param cluster: cluster id or name
        :param resource_group: resource group of the cluster (optional)
        :return: K8S cluster kube-config
        """

        request = requests.Request("GET",
                                   KUBERNETES_CLUSTER_URL_TEMPLATE.format(path=GET_K8S_CLUSTER_KUBE_CONFIG.format(
                                       cluster=cluster))
                                   )

        if request.headers:
            request.headers.update({"Auth-Resource-Group": resource_group})
        else:
            request.headers = {"Auth-Resource-Group": resource_group}

        response = self._execute_request(request, "K8S_KUBE_CONFIG")
        return response
