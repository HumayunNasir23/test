"""
This file contains Client for images related APIs
"""
import requests

from .paths import CREATE_IMAGE_PATH, DELETE_IMAGE_PATH, GET_IMAGE_PATH, GET_OPERATING_SYSTEM_PATH, LIST_IMAGES_PATH, \
    LIST_OPERATING_SYSTEMS_PATH
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class ImagesClient(BaseClient):
    """
    Client for images related APIs
    """

    def __init__(self, cloud_id):
        super(ImagesClient, self).__init__(cloud_id)

    def list_images(self, region, visibility=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param visibility:
        :param limit: Number of Resources Per Page
        :return:
        """
        if visibility and visibility not in ["private", "public"]:
            raise IBMInvalidRequestError("Parameter 'visibility' should be one of ['private', 'public']")

        params = {
            "visibility": visibility,
            "limit": limit
        }

        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_IMAGES_PATH), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "images")

        return response["images"]

    def create_image(self, region, image_json):
        """

        :param region:
        :param image_json:
        :return:
        """
        if not isinstance(image_json, dict):
            raise IBMInvalidRequestError("Parameter 'image_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request("POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_IMAGE_PATH), json=image_json)

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_image(self, region, image_id):
        """

        :param region:
        :param image_id:
        :return:
        """
        request = requests.Request("DELETE", VPC_URL_TEMPLATE.format(
            region=region, path=DELETE_IMAGE_PATH.format(image_id=image_id)))

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_image(self, region, image_id):
        """

        :param region:
        :param image_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_IMAGE_PATH.format(image_id=image_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_image(self, region, image_id):
        """

        :param region:
        :param image_id:
        :return:
        """
        raise NotImplementedError()

    def list_operating_systems(self, region, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            "limit": limit
        }
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_OPERATING_SYSTEMS_PATH),
                                   params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "operating_systems")

        return response.get("operating_systems", [])

    def get_operating_system(self, region, operating_system_name):
        """

        :param region:
        :param operating_system_name:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=GET_OPERATING_SYSTEM_PATH.format(operating_system_name=operating_system_name)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
