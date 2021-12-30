"""
This file contains Client for geography related APIs
"""
import requests

from .paths import GET_REGION_PATH, GET_ZONE_PATH, LIST_REGIONS_PATH, LIST_ZONES_IN_REGION_PATH
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_REGION
from ..urls import VPC_URL_TEMPLATE


class GeographyClient(BaseClient):
    """
    Client for geography related APIs
    """

    def __init__(self, cloud_id):
        super(GeographyClient, self).__init__(cloud_id)

    def list_regions(self):
        """

        :return:
        """
        # TODO: Write a robust method for default region (fallback region in case one is not available)
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=VPC_DEFAULT_REGION, path=LIST_REGIONS_PATH))

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("regions", [])

    def get_region(self, region):
        """

        :param region:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=VPC_DEFAULT_REGION, path=GET_REGION_PATH.format(region_name=region))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_zones_in_region(self, region):
        """

        :param region:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=VPC_DEFAULT_REGION, path=LIST_ZONES_IN_REGION_PATH.format(region_name=region))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("zones", [])

    def get_zone(self, region, zone):
        """

        :param region:
        :param zone:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(region=VPC_DEFAULT_REGION, path=GET_ZONE_PATH.format(region_name=region, zone_name=zone))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
