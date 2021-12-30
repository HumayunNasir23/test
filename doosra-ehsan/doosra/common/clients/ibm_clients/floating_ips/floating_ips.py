"""
This file contains Client for floating ip related APIs
"""
import requests

from .paths import GET_FLOATING_IP_PATH, LIST_FLOATING_IPS_PATH, RELEASE_FLOATING_IP_PATH, RESERVE_FLOATING_IP_PATH
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class FloatingIPsClient(BaseClient):
    """
    Client for floating ip related APIs
    """

    def __init__(self, cloud_id):
        super(FloatingIPsClient, self).__init__(cloud_id)

    def list_floating_ips(self, region, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            'limit': limit
        }
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_FLOATING_IPS_PATH),
                                   params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "floating_ips")

        return response["floating_ips"]

    def reserve_floating_ip(self, region, floating_ip_json):
        """

        :param region:
        :param floating_ip_json:
        :return:
        """
        if not isinstance(floating_ip_json, dict):
            raise IBMInvalidRequestError("Parameter 'floating_ip_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=RESERVE_FLOATING_IP_PATH), json=floating_ip_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def release_floating_ip(self, region, floating_ip_id):
        """

        :param region:
        :param floating_ip_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(region=region, path=RELEASE_FLOATING_IP_PATH.format(floating_ip_id=floating_ip_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_floating_ip(self, region, floating_ip_id):
        """

        :param region:
        :param floating_ip_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_FLOATING_IP_PATH.format(floating_ip_id=floating_ip_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_floating_ip(self, region, floating_ip_id):
        """

        :param region:
        :param floating_ip_id:
        :return:
        """
        raise NotImplementedError()
