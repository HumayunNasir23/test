"""
This file contains Client for network ACL related APIs
"""
import requests

from .paths import LIST_NETWORK_ACLS_PATH, CREATE_NETWORK_ACL_PATH, DELETE_NETWORK_ACL_PATH, \
    GET_NETWORK_ACL_PATH, UPDATE_NETWORK_ACL_PATH, LIST_NETWORK_ACL_RULES_PATH, CREATE_NETWORK_ACL_RULE_PATH, \
    DELETE_NETWORK_ACL_RULE_PATH, GET_NETWORK_ACL_RULE_PATH, UPDATE_NETWORK_ACL_RULE_PATH
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class NetworkACLsClient(BaseClient):
    """
    Client for network ACL related APIs
    """

    def __init__(self, cloud_id):
        super(NetworkACLsClient, self).__init__(cloud_id)

    def list_network_acls(self, region, resource_group_id=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
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
            "GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_NETWORK_ACLS_PATH), params=params
        )

        response = self._paginate_resource(request, "VPC_RESOURCE", "network_acls")

        return response["network_acls"]

    def create_network_acl(self, region, network_acl_json):
        """

        :param region:
        :param network_acl_json:
        :return:
        """
        if not isinstance(network_acl_json, dict):
            raise IBMInvalidRequestError("Parameter 'network_acl_json' should be a dictionary")

        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_NETWORK_ACL_PATH), json=network_acl_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_network_acl(self, region, network_acl_id):
        """

        :param region:
        :param network_acl_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(region=region, path=DELETE_NETWORK_ACL_PATH.format(network_acl_id=network_acl_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_network_acl(self, region, network_acl_id):
        """

        :param region:
        :param network_acl_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_NETWORK_ACL_PATH.format(network_acl_id=network_acl_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_network_acl(self, region, network_acl_id, network_acl_json):
        """

        :param region:
        :param network_acl_id:
        :param network_acl_json:
        :return:
        """
        if not isinstance(network_acl_json, dict):
            raise IBMInvalidRequestError("Parameter 'ssh_key' should be a dictionary")

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region, path=UPDATE_NETWORK_ACL_PATH.format(network_acl_id=network_acl_id), json=network_acl_json
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_network_acl_rules(self, region, network_acl_id, direction=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param network_acl_id:
        :param direction:
        :param limit: Number of Resources Per Page
        :return:
        """
        if direction and direction not in ["inbound", "outbound"]:
            raise IBMInvalidRequestError("Parameter 'direction' should be one of ['inbound', 'outbound']")

        params = {
            "direction": direction,
            "limit": limit
        }

        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(region=region, path=LIST_NETWORK_ACL_RULES_PATH.format(network_acl_id=network_acl_id)),
            params=params
        )

        response = self._paginate_resource(request, "VPC_RESOURCE", "rules")

        return response["rules"]

    def create_network_acl_rule(self, region, network_acl_id, network_acl_rule_json):
        """

        :param region:
        :param network_acl_id:
        :param network_acl_rule_json:
        :return:
        """
        if not isinstance(network_acl_rule_json, dict):
            raise IBMInvalidRequestError("Parameter 'network_acl_rule_json' should be a dictionary")

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(region=region, path=CREATE_NETWORK_ACL_RULE_PATH.format(network_acl_id=network_acl_id)),
            json=network_acl_rule_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_network_acl_rule(self, region, network_acl_id, network_acl_rule_id):
        """

        :param region:
        :param network_acl_id:
        :param network_acl_rule_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_NETWORK_ACL_RULE_PATH.format(network_acl_id=network_acl_id, rule_id=network_acl_rule_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_network_acl_rule(self, region, network_acl_id, network_acl_rule_id):
        """

        :param region:
        :param network_acl_id:
        :param network_acl_rule_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_NETWORK_ACL_RULE_PATH.format(network_acl_id=network_acl_id, rule_id=network_acl_rule_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_network_acl_rule(self, region, network_acl_id, network_acl_rule_id, network_acl_rule_json):
        """

        :param region:
        :param network_acl_id:
        :param network_acl_rule_id:
        :param network_acl_rule_json:
        :return:
        """
        if not isinstance(network_acl_rule_json, dict):
            raise IBMInvalidRequestError("Parameter 'network_acl_rule_json' should be a dictionary")

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_NETWORK_ACL_RULE_PATH.format(network_acl_id=network_acl_id, rule_id=network_acl_rule_id)
            ),
            json=network_acl_rule_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
