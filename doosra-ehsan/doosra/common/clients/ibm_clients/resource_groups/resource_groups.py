import requests

from .paths import *
from ..base_client import BaseClient
from ..urls import RESOURCE_MANAGER_URL_TEMPLATE


class ResourceGroupsClient(BaseClient):
    """
    Client for Resource Group related APIs
    """

    def __init__(self, cloud_id):
        super(ResourceGroupsClient, self).__init__(cloud_id)

    def list_resource_groups(self):
        request = requests.Request("GET", RESOURCE_MANAGER_URL_TEMPLATE.format(path=LIST_RESOURCE_GROUPS_PATH))

        response = self._execute_request(request, "RESOURCE_GROUP")

        return response["resources"]

    def get_resource_group(self, resource_group_id):
        """

        :param resource_group_id:
        :return:
        """
        request = requests.Request(
            "GET",
            RESOURCE_MANAGER_URL_TEMPLATE.format(
                path=GET_RESOURCE_GROUP_PATH.format(resource_group_id=resource_group_id)
            )
        )

        response = self._execute_request(request, "RESOURCE_GROUP")

        return response
