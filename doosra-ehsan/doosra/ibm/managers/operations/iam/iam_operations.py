import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, ReadTimeout, RequestException
from urllib3.exceptions import MaxRetryError, ReadTimeoutError
from urllib3.util.retry import Retry

from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.operations.iam.consts import IAM_BASE_URL
from doosra.ibm.managers.operations.iam.iam_patterns import *


class IAMOperations(object):
    def __init__(self, cloud):
        self.cloud = cloud
        self.base_url = IAM_BASE_URL
        self.session = self.requests_retry_session()

    def authenticate_cloud_account(self):
        """
        Authenticate IBM Cloud account and return IAM token
        :return:
        """
        request = self.format_api_url(AUTHENTICATE_IBM_PATTERN, base_url=self.base_url)
        return self.execute(request, self.cloud.to_json_body())

    @staticmethod
    def format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the unformatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def requests_retry_session(self, retries=5):
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 504),
            method_whitelist=["GET", "PUT", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount(self.base_url, adapter)
        return self.session

    def execute(self, request, data=None):
        try:
            current_app.logger.debug("{0} : {1}".format(request[0], request[1]))
            response = self.session.request(request[0], request[1], data=data, timeout=50)
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request[1])
        if response.status_code in [401, 403]:
            raise IBMAuthError(self.cloud.id)
        elif response.status_code in [400, 404, 408, 500]:
            raise IBMExecuteError(response)
        elif response.status_code == 409:
            raise IBMInvalidRequestError(response)
        elif response.status_code not in [200, 201, 204]:
            raise IBMExecuteError(response)
        return response.json()
