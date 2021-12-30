"""
This file contains Client for ssh keys related APIs
"""
import requests

from .paths import LIST_SSH_KEYS_PATH, CREATE_SSH_KEY_PATH, DELETE_SSH_KEY_PATH, GET_SSH_KEY_PATH, \
    UPDATE_SSH_KEY_PATH
from ..base_client import BaseClient
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class SSHKeysClient(BaseClient):
    """
    Client for ssh keys related APIs
    """

    def __init__(self, cloud_id):
        super(SSHKeysClient, self).__init__(cloud_id)

    def list_ssh_keys(self, region, resource_group_id=None):
        """

        :param region:
        :param resource_group_id:
        :return:
        """
        params = {"resource_group.id": resource_group_id}

        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_SSH_KEYS_PATH), params=params)

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("keys", [])

    def create_ssh_key(self, region, key_json):
        """

        :param region:
        :param key_json:
        :return:
        """
        if not isinstance(key_json, dict):
            raise IBMInvalidRequestError("Parameter 'key_json' should be a dictionary")

        request = requests.Request("POST", VPC_URL_TEMPLATE(region=region, path=CREATE_SSH_KEY_PATH), json=key_json)

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_ssh_key(self, region, key_id):
        """

        :param region:
        :param key_id:
        :return:
        """
        request = requests.Request(
            "DELETE", VPC_URL_TEMPLATE.format(region=region, path=DELETE_SSH_KEY_PATH.format(key_id=key_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_ssh_key(self, region, key_id):
        """

        :param region:
        :param key_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_SSH_KEY_PATH.format(key_id=key_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_ssh_key(self, region, key_id, key_json):
        """

        :param region:
        :param key_id:
        :param key_json:
        :return:
        """
        if not isinstance(key_json, dict):
            raise IBMInvalidRequestError("Parameter 'ssh_key' should be a dictionary")

        request = requests.Request(
            "PATCH", VPC_URL_TEMPLATE.format(region=region, path=UPDATE_SSH_KEY_PATH.format(key_id=key_id), json=key_json)
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
