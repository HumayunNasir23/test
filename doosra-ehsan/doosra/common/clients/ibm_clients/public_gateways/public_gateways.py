"""
This file contains Client for public gateways related APIs
"""
import requests

from .paths import *
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class PublicGatewaysClient(BaseClient):
    """
    Client for public gateways related APIs
    """

    def __init__(self, cloud_id):
        super(PublicGatewaysClient, self).__init__(cloud_id)

    def list_public_gateways(self, region, resource_group_id=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
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

        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_PUBLIC_GATEWAYS_PATH), params=params
        )

        response = self._paginate_resource(request, "VPC_RESOURCE", "public_gateways")

        return response["public_gateways"]

    def create_public_gateway(self, region, public_gateway_json):
        """

        :param region:
        :param public_gateway_json:
        :return:
        """
        if not isinstance(public_gateway_json, dict):
            raise IBMInvalidRequestError("Parameter 'public_gateway_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_PUBLIC_GATEWAY_PATH), json=public_gateway_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_public_gateway(self, region, public_gateway_id):
        """

        :param region:
        :param public_gateway_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region, path=DELETE_PUBLIC_GATEWAY_PATH.format(public_gateway_id=public_gateway_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_public_gateway(self, region, public_gateway_id):
        """

        :param region:
        :param public_gateway_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(region=region, path=GET_PUBLIC_GATEWAY_PATH.format(public_gateway_id=public_gateway_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_public_gateway(self, region, public_gateway_id, public_gateway_json):
        """

        :param region:
        :param public_gateway_id:
        :param public_gateway_json:
        :return:
        """
        if not isinstance(public_gateway_json, dict):
            raise IBMInvalidRequestError("Parameter 'public_gateway_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region, path=UPDATE_PUBLIC_GATEWAY_PATH.format(public_gateway_id=public_gateway_id)
            ),
            json=public_gateway_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
