"""
This file contains Client for volumes related APIs
"""
import requests

from .paths import LIST_VOLUME_PROFILES_PATH, GET_VOLUME_PROFILE_PATH, LIST_VOLUMES_PATH, CREATE_VOLUME_PATH, \
    DELETE_VOLUME_PATH, GET_VOLUME_PATH, UPDATE_VOLUME_PATH
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class VolumesClient(BaseClient):
    """
    Client for volumes related APIs
    """

    def __init__(self, cloud_id):
        super(VolumesClient, self).__init__(cloud_id)

    def list_volume_profiles(self, region, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            "limit": limit
        }
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_VOLUME_PROFILES_PATH),
                                   params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "volume_profiles")

        return response["volume_profiles"]

    def get_volume_profile(self, region, volume_profile_name):
        """

        :param region:
        :param volume_profile_name:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=GET_VOLUME_PROFILE_PATH.format(volume_profile_name=volume_profile_name)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_volumes(self, region, name=None, zone=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param name:
        :param zone:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            "name": name,
            "zone.name": zone,
            "limit": limit
        }
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_VOLUMES_PATH), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "volumes")

        return response["volumes"]

    def create_volume(self, region, volume_json):
        """

        :param region:
        :param volume_json:
        :return:
        """
        if not isinstance(volume_json, dict):
            raise IBMInvalidRequestError("Parameter 'volume_json' should be a dictionary")

        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_VOLUME_PATH), json=volume_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_volume(self, region, volume_id):
        """

        :param region:
        :param volume_id:
        :return:
        """
        request = requests.Request(
            "DELETE", VPC_URL_TEMPLATE.format(region=region, path=DELETE_VOLUME_PATH.format(volume_id=volume_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_volume(self, region, volume_id):
        """

        :param region:
        :param volume_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_VOLUME_PATH.format(volume_id=volume_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_volume(self, region, volume_id, volume_json):
        """

        :param region:
        :param volume_id:
        :param volume_json:
        :return:
        """
        if not isinstance(volume_json, dict):
            raise IBMInvalidRequestError("Parameter 'volume_json' should be a dictionary")

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(region=region, path=UPDATE_VOLUME_PATH.format(volume_id=volume_id)),
            json=volume_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
