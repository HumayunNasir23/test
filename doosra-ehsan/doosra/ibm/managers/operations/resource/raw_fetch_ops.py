from flask import current_app
from requests.exceptions import ConnectionError, ReadTimeout, RequestException
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.operations.resource.consts import GENERATION, VERSION
from doosra.models import IBMCredentials
from .resource_patterns import GET_RESOURCE_GROUP_PATTERN


class RawFetchOperations(object):
    def __init__(self, cloud, base_url, session, iam_ops,  k8s_base_url=None, session_k8s=None):
        self.cloud = cloud
        self.base_url = base_url
        self.k8s_base_url = k8s_base_url
        self.session = session
        self.session_k8s = session_k8s
        self.iam_ops = iam_ops

    def get_resource_groups(self):
        """
        Fetch resource groups.
        :return:
        """
        response = self.execute(self.format_api_url(GET_RESOURCE_GROUP_PATTERN))
        resource_groups = response.get('resources')
        if not resource_groups:
            return []

        return [{'name': group['name'],
                 'id': group['id']
                 } for group in resource_groups]

    @staticmethod
    def format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the unformatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def execute(self, request, data=None):
        request_url = request[1].format(base_url=self.base_url, version=VERSION, generation=GENERATION)
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)
        try:
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(IBMCredentials(self.iam_ops.authenticate_cloud_account()))
            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.debug("{0} : {1}".format(request[0], request_url))
            response = self.session.request(request[0], request_url, data=data, timeout=50, headers=headers)
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request_url)
        else:
            if response.status_code in [401]:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code in [400, 404, 408, 500]:
                raise IBMExecuteError(response)
            elif response.status_code == 409:
                raise IBMInvalidRequestError(response)
            elif response.status_code not in [200, 201, 204]:
                raise IBMExecuteError(response)
            return response.json()

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
        return resp
