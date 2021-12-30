"""
This file contains Client for load balancer related APIs
"""
import requests

from .paths import LIST_LOAD_BALANCERS_PATH, CREATE_LOAD_BALANCER_PATH, DELETE_LOAD_BALANCER_PATH, \
    GET_LOAD_BALANCER_PATH, \
    UPDATE_LOAD_BALANCER_PATH, LIST_LOAD_BALANCER_LISTENERS_PATH, CREATE_LOAD_BALANCER_LISTENER_PATH, \
    DELETE_LOAD_BALANCER_LISTENER_PATH, \
    GET_LOAD_BALANCER_LISTENER_PATH, UPDATE_LOAD_BALANCER_LISTENER_PATH, LIST_LOAD_BALANCER_POOLS_PATH, \
    CREATE_LOAD_BALANCER_POOL_PATH, \
    LIST_LOAD_BALANCER_LISTENER_POLICIES_PATH, \
    DELETE_LOAD_BALANCER_POOL_PATH, GET_LOAD_BALANCER_POOL_PATH, UPDATE_LOAD_BALANCER_POOL_PATH, \
    LIST_LOAD_BALANCER_POOL_MEMBERS_PATH, \
    CREATE_LOAD_BALANCER_POOL_MEMBER_PATH, DELETE_LOAD_BALANCER_POOL_MEMBER_PATH, GET_LOAD_BALANCER_POOL_MEMBER_PATH, \
    UPDATE_LOAD_BALANCER_POOL_MEMBER_PATH, UPDATE_LOAD_BALANCER_POOL_MEMBERS_PATH
from ..base_client import BaseClient
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class LoadBalancersClient(BaseClient):
    """
    Client for load balancer related APIs
    """

    def __init__(self, cloud_id):
        super(LoadBalancersClient, self).__init__(cloud_id)

    def list_load_balancers(self, region):
        """

        :param region:
        :return:
        """
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_LOAD_BALANCERS_PATH))

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("load_balancers", [])

    def create_load_balancer(self, region, load_balancer_json):
        """

        :param region:
        :param load_balancer_json:
        :return:
        """
        if not isinstance(load_balancer_json, dict):
            raise IBMInvalidRequestError("Parameter 'load_balancer_json' should be a dictionary")

        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_LOAD_BALANCER_PATH), json=load_balancer_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_load_balancer(self, region, load_balancer_id):
        """

        :param region:
        :param load_balancer_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region, path=DELETE_LOAD_BALANCER_PATH.format(load_balancer_id=load_balancer_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_load_balancer(self, region, load_balancer_id):
        """

        :param region:
        :param load_balancer_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=GET_LOAD_BALANCER_PATH.format(load_balancer_id=load_balancer_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_load_balancer(self, region, load_balancer_id, load_balancer_json):
        """

        :param region:
        :param load_balancer_id:
        :param load_balancer_json:
        :return:
        """
        if not isinstance(load_balancer_json, dict):
            raise IBMInvalidRequestError("Parameter 'ssh_key' should be a dictionary")

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region, path=UPDATE_LOAD_BALANCER_PATH.format(load_balancer_id=load_balancer_id)
            ),
            json=load_balancer_json)

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_load_balancer_listeners(self, region, load_balancer_id):
        """

        :param region:
        :param load_balancer_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_LOAD_BALANCER_LISTENERS_PATH.format(load_balancer_id=load_balancer_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("listeners", [])

    def create_load_balancer_listener(self, region, load_balancer_id, load_balancer_listener_json):
        """

        :param region:
        :param load_balancer_id:
        :param load_balancer_listener_json:
        :return:
        """
        if not isinstance(load_balancer_listener_json, dict):
            raise IBMInvalidRequestError("Parameter 'load_balancer_listener_json' should be a dictionary")

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(
                region=region, path=CREATE_LOAD_BALANCER_LISTENER_PATH.format(load_balancer_id=load_balancer_id)
            ),
            json=load_balancer_listener_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_load_balancer_listener(self, region, load_balancer_id, listener_id):
        """

        :param region:
        :param load_balancer_id:
        :param listener_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_LOAD_BALANCER_LISTENER_PATH.format(
                    load_balancer_id=load_balancer_id, listener_id=listener_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_load_balancer_listener(self, region, load_balancer_id, listener_id):
        """

        :param region:
        :param load_balancer_id:
        :param listener_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_LOAD_BALANCER_LISTENER_PATH.format(load_balancer_id=load_balancer_id, listener_id=listener_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_load_balancer_listener(self, region, load_balancer_id, listener_id, load_balancer_listener_json):
        """

        :param region:
        :param load_balancer_id:
        :param listener_id:
        :param load_balancer_listener_json:
        :return:
        """
        if not isinstance(load_balancer_listener_json, dict):
            raise IBMInvalidRequestError("Parameter 'load_balancer_listener_json' should be a dictionary")

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_LOAD_BALANCER_LISTENER_PATH.format(
                    load_balancer_id=load_balancer_id, listener_id=listener_id
                )
            ),
            json=load_balancer_listener_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_load_balancer_listener_policies(self, region, load_balancer_id, listener_id):
        """

        :param region:
        :param load_balancer_id:
        :param listener_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(
                region=region,
                path=LIST_LOAD_BALANCER_LISTENER_POLICIES_PATH.format(
                    load_balancer_id=load_balancer_id, listener_id=listener_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("listeners", [])

    def list_load_balancer_pools(self, region, load_balancer_id):
        """

        :param region:
        :param load_balancer_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_LOAD_BALANCER_POOLS_PATH.format(load_balancer_id=load_balancer_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("pools", [])

    def create_load_balancer_pool(self, region, load_balancer_id, load_balancer_pool_json):
        """

        :param region:
        :param load_balancer_id:
        :param load_balancer_pool_json:
        :return:
        """
        if not isinstance(load_balancer_pool_json, dict):
            raise IBMInvalidRequestError("Parameter 'load_balancer_pool_json' should be a dictionary")

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(
                region=region, path=CREATE_LOAD_BALANCER_POOL_PATH.format(load_balancer_id=load_balancer_id)
            ),
            json=load_balancer_pool_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_load_balancer_pool(self, region, load_balancer_id, pool_id):
        """

        :param region:
        :param load_balancer_id:
        :param pool_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_LOAD_BALANCER_POOL_PATH.format(load_balancer_id=load_balancer_id, pool_id=pool_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_load_balancer_pool(self, region, load_balancer_id, pool_id):
        """

        :param region:
        :param load_balancer_id:
        :param pool_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_LOAD_BALANCER_POOL_PATH.format(load_balancer_id=load_balancer_id, pool_id=pool_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_load_balancer_pool(self, region, load_balancer_id, pool_id, load_balancer_pool_json):
        """

        :param region:
        :param load_balancer_id:
        :param pool_id:
        :param load_balancer_pool_json:
        :return:
        """
        if not isinstance(load_balancer_pool_json, dict):
            raise IBMInvalidRequestError("Parameter 'load_balancer_listener_json' should be a dictionary")

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_LOAD_BALANCER_POOL_PATH.format(load_balancer_id=load_balancer_id, pool_id=pool_id)
            ),
            json=load_balancer_pool_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_load_balancer_pool_members(self, region, load_balancer_id, pool_id):
        """

        :param region:
        :param load_balancer_id:
        :param pool_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=LIST_LOAD_BALANCER_POOL_MEMBERS_PATH.format(load_balancer_id=load_balancer_id, pool_id=pool_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("members", [])

    def create_load_balancer_pool_member(self, region, load_balancer_id, pool_id, pool_member_json):
        """

        :param region:
        :param load_balancer_id:
        :param pool_id:
        :param pool_member_json:
        :return:
        """
        if not isinstance(pool_member_json, dict):
            raise IBMInvalidRequestError("Parameter 'pool_member_json' should be a dictionary")

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=CREATE_LOAD_BALANCER_POOL_MEMBER_PATH.format(load_balancer_id=load_balancer_id, pool_id=pool_id)
            ),
            json=pool_member_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_load_balancer_pool_member(self, region, load_balancer_id, pool_id, member_id):
        """

        :param region:
        :param load_balancer_id:
        :param pool_id:
        :param member_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_LOAD_BALANCER_POOL_MEMBER_PATH.format(
                    load_balancer_id=load_balancer_id, pool_id=pool_id, member_id=member_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_load_balancer_pool_member(self, region, load_balancer_id, pool_id, member_id):
        """

        :param region:
        :param load_balancer_id:
        :param pool_id:
        :param member_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_LOAD_BALANCER_POOL_MEMBER_PATH.format(
                    load_balancer_id=load_balancer_id, pool_id=pool_id, member_id=member_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_load_balancer_pool_member(self, region, load_balancer_id, pool_id, member_id, pool_member_json):
        """

        :param region:
        :param load_balancer_id:
        :param pool_id:
        :param member_id:
        :param pool_member_json:
        :return:
        """
        if not isinstance(pool_member_json, dict):
            raise IBMInvalidRequestError("Parameter 'pool_member_json' should be a dictionary")

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_LOAD_BALANCER_POOL_MEMBER_PATH.format(
                    load_balancer_id=load_balancer_id, pool_id=pool_id, member_id=member_id
                )
            ),
            json=pool_member_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_load_balancer_pool_members(self, region, load_balancer_id, pool_id, pool_member_list):
        """
         This API call documentation does not specify everything clearly
        :param region:
        :param load_balancer_id:
        :param pool_id:
        :param pool_member_list:
        :return:
        """
        if not isinstance(pool_member_list, list):
            raise IBMInvalidRequestError("Parameter 'pool_member_json' should be a list")

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_LOAD_BALANCER_POOL_MEMBERS_PATH.format(load_balancer_id=load_balancer_id, pool_id=pool_id)
            ),
            json=pool_member_list
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
