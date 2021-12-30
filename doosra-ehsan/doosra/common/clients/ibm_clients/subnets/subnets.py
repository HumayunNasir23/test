"""
This file contains Client for subnet related APIs
"""
import requests

from .paths import LIST_SUBNETS_PATHS, CREATE_SUBNET_PATH, DELETE_SUBNET_PATH, GET_SUBNET_PATH, UPDATE_SUBNET_PATH, \
    GET_ATTACHED_ACL, ATTACH_ACL_TO_SUBNET, DETACH_PUBLIC_GATEWAY_FROM_SUBNET, GET_ATTACHED_PUBLIC_GATEWAY_TO_SUBNET, \
    ATTACH_PUBLIC_GATEWAY_TO_SUBNET
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..urls import VPC_URL_TEMPLATE


class SubnetsClient(BaseClient):
    """
    Client for subnet related APIs
    """

    def __init__(self, cloud_id):
        super(SubnetsClient, self).__init__(cloud_id)

    def list_subnets(self, region, resource_group_id=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param resource_group_id:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            "resource_group.id": resource_group_id,
            "limit": limit
        }

        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_SUBNETS_PATHS), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "subnets")

        return response["subnets"]

    def create_subnet(self, region, subnet_json):
        """

        :param region:
        :param subnet_json:
        :return:
        """
        # TODO: Create schema for input and validate it
        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_SUBNET_PATH), json=subnet_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_subnet(self, region, subnet_id):
        """

        :param region:
        :param subnet_id:
        :return:
        """
        request = requests.Request(
            "DELETE", VPC_URL_TEMPLATE.format(region=region, path=DELETE_SUBNET_PATH.format(subnet_id=subnet_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_subnet(self, region, subnet_id):
        """

        :param region:
        :param subnet_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_SUBNET_PATH.format(subnet_id=subnet_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_subnet(self, region, subnet_id, subnet_json):
        """

        :param region:
        :param subnet_id:
        :param subnet_json:
        :return:
        """
        # TODO: Create schema for input and validate it
        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(region=region, path=UPDATE_SUBNET_PATH.format(subnet_id=subnet_id)),
            json=subnet_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_attached_network_acl_to_subnet(self, region, subnet_id):
        """

        :param region:
        :param subnet_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_ATTACHED_ACL.format(subnet_id=subnet_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def attach_acl_to_subnet(self, region, subnet_id, attach_subnet_json):
        """

        :param region:
        :param subnet_id:
        :param attach_subnet_json:
        :return:
        """
        request = requests.Request(
            "PUT",
            VPC_URL_TEMPLATE.format(region=region, path=ATTACH_ACL_TO_SUBNET.format(subnet_id=subnet_id)),
            json=attach_subnet_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def detach_pg_from_subnet(self, region, subnet_id):
        """

        :param region:
        :param subnet_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(region=region, path=DETACH_PUBLIC_GATEWAY_FROM_SUBNET.format(subnet_id=subnet_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_attached_pg_to_subnet(self, region, subnet_id):
        """

        :param region:
        :param subnet_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(region=region, path=GET_ATTACHED_PUBLIC_GATEWAY_TO_SUBNET.format(subnet_id=subnet_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def attach_pg_to_subnet(self, region, subnet_id, attach_pg_json):
        """

        :param region:
        :param subnet_id:
        :param attach_pg_json:
        :return:
        """
        request = requests.Request(
            "PUT",
            VPC_URL_TEMPLATE.format(region=region, path=ATTACH_PUBLIC_GATEWAY_TO_SUBNET.format(subnet_id=subnet_id)),
            json=attach_pg_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
