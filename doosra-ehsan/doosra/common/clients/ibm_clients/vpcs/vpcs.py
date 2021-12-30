"""
This file contains Client for VPC related tasks
"""
import requests

from .paths import *
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE

from ..exceptions import IBMInvalidRequestError

class VPCsClient(BaseClient):
    """
    Client for VPC related tasks
    """

    def __init__(self, cloud_id):
        super(VPCsClient, self).__init__(cloud_id)

    def list_vpcs(self, region, resource_group_id=None, classic_access=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param resource_group_id:
        :param classic_access:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            "resource_group.id": resource_group_id,
            "classic_access": classic_access,
            "limit": limit
        }

        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_VPCS_PATH), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "vpcs")

        return response.get("vpcs", [])

    def create_vpc(self, region, vpc_json):
        """

        :param region:
        :param vpc_json:
        :return:
        """
        if not isinstance(vpc_json, dict):
            raise IBMInvalidRequestError("Parameter 'vpc_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request("POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_VPC_PATH), json=vpc_json)

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_vpc(self, region, vpc_id):
        """

        :param region:
        :param vpc_id:
        :return:
        """
        request = requests.Request(
            "DELETE", VPC_URL_TEMPLATE.format(region=region, path=DELETE_VPC_PATH.format(vpc_id=vpc_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_vpc(self, region, vpc_id):
        """

        :param region:
        :param vpc_id:
        :return:
        """
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=GET_VPC_PATH.format(vpc_id=vpc_id)))

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_vpc(self, region, vpc_id, vpc_json):
        """

        :param region:
        :param vpc_id:
        :param vpc_json:
        :return:
        """
        if not isinstance(vpc_json, dict):
            raise IBMInvalidRequestError("Parameter 'vpc_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "PATCH", VPC_URL_TEMPLATE.format(region=region, path=UPDATE_VPC_PATH.format(vpc_id=vpc_id)), json=vpc_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_vpcs_default_network_acl(self, region, vpc_id):
        """

        :param region:
        :param vpc_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_VPCS_DEFAULT_NETWORK_ACL_PATH.format(vpc_id=vpc_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_vpcs_default_security_group(self, region, vpc_id):
        """

        :param region:
        :param vpc_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_VPCS_DEFAULT_SECURITY_GROUP_PATH.format(vpc_id=vpc_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_address_prefixes(self, region, vpc_id):
        """

        :param region:
        :param vpc_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_VPC_ADDRESS_PREFIXES_PATH.format(vpc_id=vpc_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("address_prefixes", [])

    def create_address_prefix(self, region, vpc_id, address_prefix_json):
        """

        :param region:
        :param vpc_id:
        :param address_prefix_json:
        :return:
        """
        if not isinstance(address_prefix_json, dict):
            raise IBMInvalidRequestError("Parameter 'address_prefix_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(region=region, path=CREATE_VPC_ADDRESS_PREFIX_PATH.format(vpc_id=vpc_id)),
            json=address_prefix_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_address_prefix(self, region, vpc_id, address_prefix_id):
        """

        :param region:
        :param vpc_id:
        :param address_prefix_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_VPC_ADDRESS_PREFIX_PATH.format(vpc_id=vpc_id, address_prefix_id=address_prefix_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_address_prefix(self, region, vpc_id, address_prefix_id):
        """

        :param region:
        :param vpc_id:
        :param address_prefix_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_VPC_ADDRESS_PREFIX_PATH.format(vpc_id=vpc_id, address_prefix_id=address_prefix_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_address_prefix(self, region, vpc_id, address_prefix_id, address_prefix_json):
        """

        :param region:
        :param vpc_id:
        :param address_prefix_id:
        :param address_prefix_json:
        :return:
        """
        if not isinstance(address_prefix_json, dict):
            raise IBMInvalidRequestError("Parameter 'address_prefix_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_VPC_ADDRESS_PREFIX_PATH.format(vpc_id=vpc_id, address_prefix_id=address_prefix_id)
            ),
            json=address_prefix_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_vpc_routes(self, region, vpc_id, zone_name=None):
        """

        :param region:
        :param vpc_id:
        :param zone_name:
        :return:
        """
        params = {"zone.name": zone_name}

        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_VPC_ROUTES_PATH.format(vpc_id=vpc_id)), params=params
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("routes", [])

    def create_vpc_route(self, region, vpc_id, vpc_route_json):
        """

        :param region:
        :param vpc_id:
        :param vpc_route_json:
        :return:
        """
        if not isinstance(vpc_route_json, dict):
            raise IBMInvalidRequestError("Parameter 'vpc_route_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(region=region, path=CREATE_VPC_ROUTE_PATH.format(vpc_id=vpc_id)),
            json=vpc_route_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_vpc_route(self, region, vpc_id, route_id):
        """

        :param region:
        :param vpc_id:
        :param route_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(region=region, path=DELETE_VPC_ROUTE_PATH.format(vpc_id=vpc_id, route_id=route_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_vpc_route(self, region, vpc_id, route_id):
        """

        :param region:
        :param vpc_id:
        :param route_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_VPC_ROUTE_PATH.format(vpc_id=vpc_id,
                                                                                         route_id=route_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_vpc_route(self, region, vpc_id, route_id, vpc_route_json):
        """

        :param region:
        :param vpc_id:
        :param route_id:
        :param vpc_route_json:
        :return:
        """
        if not isinstance(vpc_route_json, dict):
            raise IBMInvalidRequestError("Parameter 'vpc_route_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(region=region, path=UPDATE_VPC_ROUTE_PATH.format(vpc_id=vpc_id, route_id=route_id)),
            json=vpc_route_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
