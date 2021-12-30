from flask import current_app
from requests.exceptions import ConnectionError, ReadTimeout, RequestException
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

from doosra.ibm.managers.exceptions import *
from doosra.ibm.managers.operations.resource.consts import GENERATION, VERSION
from doosra.models import IBMCredentials, IBMResourceGroup
from .resource_patterns import GET_RESOURCE_GROUP_PATTERN


class FetchOperations(object):
    def __init__(self, cloud, base_url, session, iam_ops):
        self.cloud = cloud
        self.base_url = base_url
        self.session = session
        self.iam_ops = iam_ops

    def get_resource_groups(self, name=None, resource_id=None):
        """
        Manages resources organized in your account.
        :return:
        """
        resource_groups_list = list()
        resource_groups = self.execute(self.format_api_url(GET_RESOURCE_GROUP_PATTERN))
        for resource_group in resource_groups.get('resources'):
            ibm_resource_group = IBMResourceGroup(resource_group['name'], resource_group['id'], self.cloud.id)
            if not ((name and name != ibm_resource_group.name) or
                    (resource_id and resource_id != ibm_resource_group.resource_id)):
                resource_groups_list.append(ibm_resource_group)
        return resource_groups_list

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
