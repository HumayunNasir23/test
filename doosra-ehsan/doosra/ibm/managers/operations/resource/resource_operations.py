import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from doosra.ibm.managers.operations.resource.consts import RESOURCE_CONTROLLER_BASE_URL, KUBERNETES_CLUSTER_BASE_URL
from .fetch_operations import FetchOperations
from .raw_fetch_ops import RawFetchOperations


class ResourceOperations(object):
    def __init__(self, cloud, iam_ops):
        self.cloud = cloud
        self.iam_ops = iam_ops
        self.base_url = RESOURCE_CONTROLLER_BASE_URL
        self.session = self.requests_retry_session()
        self.k8s_base_url = KUBERNETES_CLUSTER_BASE_URL
        self.session_k8s = self.requests_retry_session(retries=30, k8s=True)
        self.fetch_ops = FetchOperations(self.cloud, self.base_url, self.session, self.iam_ops)
        self.raw_fetch_ops = RawFetchOperations(self.cloud, self.base_url, self.session, self.iam_ops, self.k8s_base_url, self.session_k8s)

    def requests_retry_session(self, retries=5,  k8s=None):
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 504),
            method_whitelist=["GET", "PUT", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        if k8s:
            base_url = self.k8s_base_url
        else:
            base_url = self.base_url
        self.session.mount(base_url, adapter)
        return self.session
