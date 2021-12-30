"""
This file contains Client for security group related APIs
"""
import requests

from .paths import LIST_SECURITY_GROUPS, CREATE_SECURITY_GROUP, DELETE_SECURITY_GROUP, GET_SECURITY_GROUP, \
    UPDATE_SECURITY_GROUP, LIST_SECURITY_GROUP_NETWORK_INTERFACE, REMOVE_NETWORK_INTERFACE_FROM_SECURITY_GROUP, \
    GET_NETWORK_INTERFACE_IN_SECURITY_GROUP, ADD_NETWORK_INTERFACE_TO_SECURITY_GROUP, LIST_SECURITY_GROUPS_RULES, \
    CREATE_SECURITY_GROUPS_RULES, DELETE_SECURITY_GROUPS_RULES, GET_SECURITY_GROUPS_RULES, UPDATE_SECURITY_GROUP_RULES
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..urls import VPC_URL_TEMPLATE


class SecurityGroupsClient(BaseClient):
    """
    Client for security group related APIs
    """

    def __init__(self, cloud_id):
        super(SecurityGroupsClient, self).__init__(cloud_id)

    def list_security_groups(self, region, resource_group_id=None, vpc_id=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param resource_group_id:
        :param vpc_id:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            "resource_group.id": resource_group_id,
            "vpc.id": vpc_id,
            "limit": limit
        }

        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_SECURITY_GROUPS), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "security_groups")

        return response["security_groups"]

    def create_security_group(self, region, security_group_json):
        """

        :param region:
        :param security_group_json:
        :return:
        """
        # TODO set schema to validate payload
        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_SECURITY_GROUP), json=security_group_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_security_group(self, region, security_group_id):
        """

        :param region:
        :param security_group_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(region=region, path=DELETE_SECURITY_GROUP.format(security_group_id=security_group_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_security_group(self, region, security_group_id):
        """

        :param region:
        :param security_group_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(region=region, path=GET_SECURITY_GROUP.format(security_group_id=security_group_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_security_group(self, region, security_group_id, security_group_json):
        """

        :param region:
        :param security_group_id:
        :param security_group_json:
        :return:
        """
        # TODO set schema to validate payload

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(region=region, path=UPDATE_SECURITY_GROUP.format(security_group_id=security_group_id)),
            json=security_group_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_security_group_network_interface(self, region, security_group_id):
        """

        :param region:
        :param security_group_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_SECURITY_GROUP_NETWORK_INTERFACE.format(security_group_id=security_group_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("network_interfaces", [])

    def remove_network_interface_from_security_group(self, region, security_group_id, network_interface_id):
        """

        :param region:
        :param security_group_id:
        :param network_interface_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=REMOVE_NETWORK_INTERFACE_FROM_SECURITY_GROUP.format(
                    security_group_id=security_group_id, network_inteface_id=network_interface_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_network_interface_in_security_group(self, region, security_group_id, network_interface_id):
        """

        :param region:
        :param security_group_id:
        :param network_interface_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_NETWORK_INTERFACE_IN_SECURITY_GROUP.format(
                    security_group_id=security_group_id, network_inteface_id=network_interface_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def add_network_interface_to_security_group(self, region, security_group_id, network_interface_id):
        """

        :param region:
        :param security_group_id:
        :param network_interface_id:
        :return:
        """
        request = requests.Request(
            "PUT",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=ADD_NETWORK_INTERFACE_TO_SECURITY_GROUP.format(
                    security_group_id=security_group_id, network_inteface_id=network_interface_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_security_group_rules(self, region, security_group_id):
        """

        :param region:
        :param security_group_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_SECURITY_GROUPS_RULES.format(security_group_id=security_group_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("rules", [])

    def create_security_group_rule(self, region, security_group_id, rule_json):
        """

        :param region:
        :param security_group_id:
        :param rule_json:
        :return:
        """
        # TODO set schema to validate payload
        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(
                region=region, path=CREATE_SECURITY_GROUPS_RULES.format(security_group_id=security_group_id)
            ),
            json=rule_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_security_group_rules(self, region, security_group_id, rule_id):
        """

        :param region:
        :param security_group_id:
        :param rule_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_SECURITY_GROUPS_RULES.format(security_group_id=security_group_id, rule_id=rule_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_security_group_rule(self, region, security_group_id, rule_id):
        """

        :param region:
        :param security_group_id:
        :param rule_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_SECURITY_GROUPS_RULES.format(security_group_id=security_group_id, rule_id=rule_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_security_group_rule(self, region, security_group_id, rule_id, sec_group_rule_json):
        """

        :param region:
        :param security_group_id:
        :param rule_id:
        :param sec_group_rule_json:
        :return:
        """
        # TODO set schema to validate payload
        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_SECURITY_GROUP_RULES.format(security_group_id=security_group_id, rule_id=rule_id)
            ),
            json=sec_group_rule_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
