import requests
import time
from flask import current_app, Response
from requests import ReadTimeout, RequestException
from requests.adapters import HTTPAdapter
from urllib3.exceptions import MaxRetryError, ReadTimeoutError
from urllib3.util.retry import Retry

from doosra import db as doosradb
from doosra.common.utils import decrypt_api_key
from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.operations.iam.iam_operations import IAMOperations
from doosra.models import SoftlayerCloud, IBMCloud, IBMCredentials
from .consts import *
from .paths import CREATE_VPC_KUBERNETES_CLUSTER_PATH, CREATE_VPC_KUBERNETES_WORKERPOOL_PATH, \
    GET_VPC_KUBERNETES_CLUSTER_DETAIL_PATH, GET_CLASSIC_KUBERNETES_CLUSTER_KUBE_CONFIG_PATH, \
    GET_CLASSIC_KUBERNETES_CLUSTERS_SUBNET_PATH, GET_CLASSIC_KUBERNETES_CLUSTERS_WORKER_POOLS_PATH, \
    LIST_CLASSIC_KUBERNETES_CLUSTERS_PATH, GET_VPC_KUBERNETES_CLUSTER_KUBE_CONFIG_PATH
from ..urls import AUTH_URL, CLASSIC_KUBERNETES_CLUSTERS_URL_TEMPLATE, \
    KUBERNETES_CLUSTER_URL_TEMPLATE, KUBERNETES_CLUSTER_BASE_URL


class ClassicKubernetesClient:
    """
    Client for Classic IKS Cluster related APIs
    """

    def __init__(self, user_name=None, api_key=None):
        self.user_name = user_name
        self.api_key = api_key
        self.token = self.generate_token()

    def generate_token(self):
        """
        Authenticate IBM Cloud account and return IAM token
        :return:
        """
        softlayer_cloud = doosradb.session.query(SoftlayerCloud).filter_by(
            username=self.user_name, api_key=self.api_key).first()
        if not softlayer_cloud:
            return Response("SOFTLAYER_CLOUD_NOT_FOUND", status=404)

        ibm_cloud = doosradb.session.query(IBMCloud).filter_by(id=softlayer_cloud.ibm_cloud_account_id).first()

        request = requests.post(
            AUTH_URL,
            params={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": decrypt_api_key(ibm_cloud.api_key),
                "client_id": "bx",
                "client_secret": "bx"
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
        )
        return request.json()

    def list_clusters(self):
        """
        This request lists all classic IKS Cluster on the account
        :return:
        """
        try:

            headers = {'Authorization': self.token.get('access_token')}
            response = requests.get(KUBERNETES_CLUSTER_URL_TEMPLATE.format(path=LIST_CLASSIC_KUBERNETES_CLUSTERS_PATH),
                                    headers=headers)

        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:

            current_app.logger.debug(ex)
            raise ex
        if response.status_code == 401:
            raise IBMAuthError()
        elif response.status_code not in [200, 201, 202, 204, 404]:
            raise IBMExecuteError(response)

        return response.json()

    def get_cluster_worker_pool(self, cluster):
        """
        This request retrieves the workerpools of the specified classic IKS cluster
        :return:
        """
        try:

            headers = {'Authorization': self.token.get('access_token')}
            response = requests.get(CLASSIC_KUBERNETES_CLUSTERS_URL_TEMPLATE.format(
                path=GET_CLASSIC_KUBERNETES_CLUSTERS_WORKER_POOLS_PATH.format(cluster=cluster)), headers=headers)

        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:

            current_app.logger.debug(ex)
            raise ex
        if response.status_code == 401:
            raise IBMAuthError()
        elif response.status_code not in [200, 201, 202, 204, 404]:
            raise IBMExecuteError(response)

        return response.json()

    def get_cluster_subnets(self, cluster, resource_group):
        """
        This request retrieves vlans in which classic IKS clusters are provisioned
        """

        try:
            headers = {'Authorization': self.token.get('access_token'), 'X-Auth-Resource-Group': resource_group}
            response = requests.get(CLASSIC_KUBERNETES_CLUSTERS_URL_TEMPLATE.format(
                path=GET_CLASSIC_KUBERNETES_CLUSTERS_SUBNET_PATH.format(cluster=cluster)), headers=headers)

        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:

            current_app.logger.debug(ex)
            raise ex
        if response.status_code == 401:
            raise IBMAuthError()
        elif response.status_code == 403:
            return "Free tier cluster"
        elif response.status_code not in [200, 201, 202, 204, 404]:
            raise IBMExecuteError(response)

        return response.json()

    def get_cluster_kube_config(self, cluster):
        """
        This request retrieves admin config file of the specified classic IKS cluster
        """

        try:
            headers = {'Authorization': self.token.get('access_token'),
                       'X-Auth-Refresh-Token': self.token.get('refresh_token')}

            response = requests.get(KUBERNETES_CLUSTER_URL_TEMPLATE.format(
                path=GET_CLASSIC_KUBERNETES_CLUSTER_KUBE_CONFIG_PATH.format(cluster=cluster)), headers=headers)

        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:

            current_app.logger.debug(ex)
            raise ex
        if response.status_code == 401:
            raise IBMAuthError()
        elif response.status_code not in [200, 201, 202, 204, 404]:
            raise IBMExecuteError(response)

        return response.json()


class VPCKubernetesClient:
    """
    Client for VPC Kubernetes Cluster related APIs
    """

    def __init__(self, cloud_id):
        self.cloud_id = cloud_id
        self.kubernetes_base_url = KUBERNETES_CLUSTER_BASE_URL
        self.session = self.requests_retry_session()

    def create_cluster(self, cluster):
        """
        This request creates an IKS Cluster in VPC
        """

        data = cluster.to_json_body()
        data['workerPool'].update({'vpcID': cluster.ibm_vpc_network.resource_id})

        worker_pools = list()
        workerpools = [worker_pool.to_json_body() for worker_pool in cluster.worker_pools.all()]

        if len(workerpools) > 1:
            for worker_pool in workerpools:
                if worker_pool['name'] == data['workerPool']['name']:
                    continue
                worker_pool["vpcID"] = cluster.ibm_vpc_network.resource_id
                worker_pools.append(worker_pool)

        response = self.execute(
            self.format_api_url(CREATE_VPC_KUBERNETES_CLUSTER_PATH),
            cluster,
            worker_pools,
            data, "normal")
        return response

    def get_cluster_status(self, cluster_id):
        """
        This request retrieves a single iks cluster specified by the identifier in the URL.
        :return:
        """

        response = self.execute(self.format_api_url(GET_VPC_KUBERNETES_CLUSTER_DETAIL_PATH, cluster=cluster_id))
        return response.get("state")

    def get_cluster_kube_config(self, cluster_id):
        """
        :param
        This request retrieves config file of the specified VPC IKS cluster.
        :return:
        """

        response = self.execute(self.format_api_url(GET_VPC_KUBERNETES_CLUSTER_KUBE_CONFIG_PATH, cluster=cluster_id))
        return response

    def requests_retry_session(self, retries=5):
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
        self.session.mount(self.kubernetes_base_url, adapter)
        return self.session

    @staticmethod
    def format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the un-formatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def wait_for_operation(self, resource_id, required_status=None):
        """
        Poll for the cluster creation or deletion operation and do so while it is completed/deleted
        :return:
        """
        cluster = self.get_cluster_status(resource_id)

        if cluster:
            while True:
                status = self.get_cluster_status(resource_id)
                if not status:
                    break

                if required_status == status:
                    return True

                elif status == FAILED:
                    return False

        return True

    def execute(self, request, cluster=None, worker_pools=None, data=None, required_status=None):
        """
        The following method executes the request on IBM Cloud and then polls for the resource creation or
        deletion operation and do so while it is completed/deleted.
        :return:
        """

        request_url = request[1].format(kubernetes_base_url=self.kubernetes_base_url)
        cloud = doosradb.session.query(IBMCloud).filter_by(id=self.cloud_id).first()
        if not cloud:
            raise IBMInvalidRequestError("Cloud not found")
        if not cloud.credentials:
            raise IBMAuthError(cloud.id)
        iam_ops = IAMOperations(cloud)

        try:
            if cloud.credentials.is_token_expired():
                cloud.credentials.update_token(IBMCredentials(iam_ops.authenticate_cloud_account()))
            headers = {"Authorization": cloud.credentials.access_token}
            current_app.logger.info("{0}: {1} {2}".format(request[0], request_url, data if data else ""))

            if headers and cluster:
                headers.update({"Auth-Refresh-Token": cloud.credentials.refresh_token,
                                "Auth-Resource-Group": cluster.ibm_resource_group.resource_id})
            else:
                headers.update({"Auth-Refresh-Token": cloud.credentials.refresh_token})
            response = self.session.request(request[0], request_url, json=data, timeout=50, headers=headers)

        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(cloud.id, request_url)

        else:
            if response.status_code == 401:
                raise IBMAuthError(cloud.id)
            elif response.status_code not in [200, 201, 202, 404]:
                raise IBMExecuteError(response)
            elif response.status_code == 201:

                if worker_pools:
                    for worker_pool in worker_pools:
                        worker_pool['cluster'] = response.json().get("clusterID")
                        try:
                            resp = self.session.request("POST", KUBERNETES_CLUSTER_URL_TEMPLATE.format(
                                path=CREATE_VPC_KUBERNETES_WORKERPOOL_PATH), json=worker_pool, timeout=50,
                                                        headers=headers)
                        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
                            current_app.logger.debug(ex)
                            raise IBMConnectError(cloud.id, request_url)
                        else:
                            if resp.status_code == 401:
                                raise IBMAuthError(cloud.id)
                            elif resp.status_code not in [200, 201]:
                                raise IBMExecuteError(resp)
            time.sleep(60)

            if response.json().get("clusterID"):
                status = self.wait_for_operation(response.json().get("clusterID"), required_status)
                if not status:
                    raise IBMInvalidRequestError(
                        "The requested operation could not be performed:\n{0} : {1}".format(request[0], request_url))

            return response.json().get("clusterID") if response.json().get("clusterID") else response.json()
