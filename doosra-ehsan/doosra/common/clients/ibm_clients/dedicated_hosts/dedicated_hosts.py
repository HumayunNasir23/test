"""
This file contains Client for Dedicated Host related APIs
"""
import requests

from .paths import *
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class DedicatedHostsClient(BaseClient):
    """
    Client for Dedicated Host APIs
    """

    def __init__(self, cloud_id):
        super(DedicatedHostsClient, self).__init__(cloud_id)

    def list_dedicated_host_groups(self, region, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """
        List all Dedicated Host Groups
        :param region: <string> Region of the IBM Cloud
        :param limit: <int> Number of Resources Per Page
        :return:
        """
        params = {
            'limit': limit
        }
        request = \
            requests.Request(
                "GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_DEDICATED_HOST_GROUPS_PATH), params=params
            )

        response = self._paginate_resource(request, "VPC_RESOURCE", "groups")

        return response["groups"]

    def create_dedicated_host_group(self, region, dedicated_host_group_json):
        """
        Create a Dedicated Host Group
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_group_json: <dict> JSON payload for the API
        :return:
        """
        if not isinstance(dedicated_host_group_json, dict):
            raise IBMInvalidRequestError("Parameter 'instance_json' should be a dictionary")

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(region=region, path=CREATE_DEDICATED_HOST_GROUP_PATH),
            json=dedicated_host_group_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_dedicated_host_group(self, region, dedicated_host_group_id):
        """
        Delete a Dedicated Host Group by ID
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_group_id: <string> ID of Dedicated Host Group on IBM
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_DEDICATED_HOST_GROUP_PATH.format(dedicated_host_group_id=dedicated_host_group_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_dedicated_host_group(self, region, dedicated_host_group_id):
        """
        Get a Dedicated Host by ID
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_group_id: <string> ID of Dedicated Host Group on IBM
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_DEDICATED_HOST_GROUP_PATH.format(dedicated_host_group_id=dedicated_host_group_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_dedicated_host_group(self, region, dedicated_host_group_id, updated_dh_group_json):
        """
        Update a dedicated host group by ID
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_group_id: <string> ID of Dedicated Host Group on IBM
        :param updated_dh_group_json: <dict> JSON payload for the API
        :return:
        """
        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_DEDICATED_HOST_GROUP_PATH.format(dedicated_host_group_id=dedicated_host_group_id)
            ),
            json=updated_dh_group_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_dedicated_host_profiles(self, region, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """
        List all Dedicated Host Profiles
        :param region: <string> Region of the IBM Cloud
        :param limit: <int> Number of Resources Per Page
        :return:
        """
        params = {
            'limit': limit
        }
        request = \
            requests.Request(
                "GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_DEDICATED_HOST_PROFILES_PATH), params=params
            )

        response = self._paginate_resource(request, "VPC_RESOURCE", "profiles")

        return response["profiles"]

    def get_dedicated_host_profile(self, region, dedicated_host_profile_name):
        """
        Get a Dedicated Host profile by name
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_profile_name: <string> Name of the Dedicated Host on IBM
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_DEDICATED_HOST_PROFILES_PATH.format(dedicated_host_profile_name=dedicated_host_profile_name)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_dedicated_hosts(self, region, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """
        List all Dedicated Hosts
        :param region: <string> Region of the IBM Cloud
        :param limit: <int> Number of Resources Per Page
        :return:
        """
        params = {
            'limit': limit
        }
        request = \
            requests.Request(
                "GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_DEDICATED_HOSTS_PATH), params=params
            )

        response = self._paginate_resource(request, "VPC_RESOURCE", "dedicated_hosts")

        return response["dedicated_hosts"]

    def create_dedicated_host(self, region, dedicated_host_json):
        """
        Create a Dedicated Host
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_json: <dict> JSON payload for the API
        :return:
        """
        if not isinstance(dedicated_host_json, dict):
            raise IBMInvalidRequestError("Parameter 'dedicated_host_json' should be a dictionary")

        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_DEDICATED_HOST_PATH), json=dedicated_host_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_dedicated_host_disks(self, region, dedicated_host_id, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """
        List all disks of a Dedicated Host
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_id: <string> ID of the Dedicated Host on IBM
        :param limit: <int> Number of Resources Per Page
        :return:
        """
        params = {
            'limit': limit
        }
        request = \
            requests.Request(
                "GET",
                VPC_URL_TEMPLATE.format(
                    region=region,
                    path=LIST_DEDICATED_HOST_DISKS_PATH.format(dedicated_host_id=dedicated_host_id)
                ),
                params=params
            )

        response = self._paginate_resource(request, "VPC_RESOURCE", "disks")

        return response["dedicated_hosts"]

    def get_dedicated_host_disk(self, region, dedicated_host_id, dedicated_host_disk_id):
        """
        Get a Dedicated Host Disk by ID
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_id: <string> ID of the Dedicated Host on IBM
        :param dedicated_host_disk_id: <string> ID of the Dedicated Host Disk on IBM
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_DEDICATED_HOST_DISK_PATH.format(
                    dedicated_host_id=dedicated_host_id,
                    dedicated_host_disk_id=dedicated_host_disk_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_dedicated_host_disk(self, region, dedicated_host_id, dedicated_host_disk_id, updated_dh_disk_json):
        """
        Update a Dedicated Host Disk by ID
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_id: <string> ID of the Dedicated Host on IBM
        :param dedicated_host_disk_id: <string> ID of the Dedicated Host on IBM
        :param updated_dh_disk_json: <dict> JSON payload for the API
        :return:
        """
        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region, path=UPDATE_DEDICATED_HOST_DISK_PATH.format(
                    dedicated_host_id=dedicated_host_id,
                    dedicated_host_disk_id=dedicated_host_disk_id
                )
            ),
            json=updated_dh_disk_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_dedicated_host(self, region, dedicated_host_id):
        """
        Delete a Dedicated Host by ID
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_id: <string> ID of the Dedicated Host on IBM
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region, path=DELETE_DEDICATED_HOST_PATH.format(dedicated_host_id=dedicated_host_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_dedicated_host(self, region, dedicated_host_id):
        """
        Get a Dedicated Host by ID
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_id: <string> ID of the Dedicated Host on IBM
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=GET_DEDICATED_HOST_PATH.format(dedicated_host_id=dedicated_host_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_dedicated_host(self, region, dedicated_host_id, updated_dh_json):
        """
        Update a Dedicated Host by ID
        :param region: <string> Region of the IBM Cloud
        :param dedicated_host_id: <string> ID of the Dedicated Host on IBM
        :param updated_dh_json: <dict> JSON payload for the API
        :return:
        """
        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region, path=UPDATE_DEDICATED_HOST_PATH.format(dedicated_host_id=dedicated_host_id)
            ),
            json=updated_dh_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
