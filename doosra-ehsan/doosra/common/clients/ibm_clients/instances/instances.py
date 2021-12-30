"""
This file contains Client for instance related APIs
"""
import requests

from .paths import *
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..exceptions import IBMInvalidRequestError
from ..urls import VPC_URL_TEMPLATE


class InstancesClient(BaseClient):
    """
    Client for instance related APIs
    """

    def __init__(self, cloud_id):
        super(InstancesClient, self).__init__(cloud_id)

    def list_instance_profiles(self, region):
        """

        :param region:
        :return:
        """
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_INSTANCE_PROFILES_PATH))

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("profiles", [])

    def get_instance_profile(self, region, instance_profile_name):
        """

        :param region:
        :param instance_profile_name:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=GET_INSTANCE_PROFILE_PATH.format(instance_profile_name=instance_profile_name)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_instances(self, region, resource_group_id=None, name=None, vpc_id=None, vpc_crn=None, vpc_name=None,
                       limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param resource_group_id:
        :param name:
        :param vpc_id:
        :param vpc_crn:
        :param vpc_name:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            "resource_group.id": resource_group_id,
            "name": name,
            "vpc.id": vpc_id,
            "vpc.crn": vpc_crn,
            "vpc.name": vpc_name,
            "limit": limit
        }

        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_INSTANCES_PATH), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "instances")

        return response["instances"]

    def create_instance(self, region, instance_json):
        """

        :param region:
        :param instance_json:
        :return:
        """
        if not isinstance(instance_json, dict):
            raise IBMInvalidRequestError("Parameter 'instance_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_INSTANCE_PATH), json=instance_json
        )

        response = self._execute_request(request, "VPC_RESOURCE", updated_api_version=True)

        return response

    def delete_instance(self, region, instance_id):
        """

        :param region:
        :param instance_id:
        :return:
        """
        request = requests.Request(
            "DELETE", VPC_URL_TEMPLATE.format(region=region, path=DELETE_INSTANCE_PATH.format(instance_id=instance_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_instance(self, region, instance_id):
        """

        :param region:
        :param instance_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_INSTANCE_PATH.format(instance_id=instance_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_instance(self, region, instance_id, instance_json):
        """

        :param region:
        :param instance_id:
        :param instance_json:
        :return:
        """
        if not isinstance(instance_json, dict):
            raise IBMInvalidRequestError("Parameter 'instance_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(region=region, path=UPDATE_INSTANCE_PATH.format(instance_id=instance_id)),
            json=instance_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_instance_init_config(self, region, instance_id):
        """

        :param region:
        :param instance_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(region=region, path=GET_INSTANCE_INIT_CONFIG_PATH.format(instance_id=instance_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def create_instance_action(self, region, instance_id, instance_action_json):
        """

        :param region:
        :param instance_id:
        :param instance_action_json:
        :return:
        """
        if not isinstance(instance_action_json, dict):
            raise IBMInvalidRequestError("Parameter 'instance_acion_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(region=region, path=CREATE_INSTANCE_ACTION_PATH.format(instance_id=instance_id)),
            json=instance_action_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_instance_network_interfaces(self, region, instance_id):
        """

        :param region:
        :param instance_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_INSTANCE_NETWORK_INTERFACES_PATH.format(instance_id=instance_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("network_interfaces", [])

    def create_network_interface(self, region, instance_id, network_interface_json):
        """

        :param region:
        :param instance_id:
        :param network_interface_json:
        :return:
        """
        if not isinstance(network_interface_json, dict):
            raise IBMInvalidRequestError("Parameter 'network_interface_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(
                region=region, path=CREATE_INSTANCE_NETWORK_INTERFACE_PATH.format(instance_id=instance_id)
            ),
            json=network_interface_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_instance_network_interface(self, region, instance_id, network_interface_id):
        """

        :param region:
        :param instance_id:
        :param network_interface_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_INSTANCE_NETWORK_INTERFACE_PATH.format(
                    instance_id=instance_id, network_interface_id=network_interface_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_instance_network_interface(self, region, instance_id, network_interface_id):
        """

        :param region:
        :param instance_id:
        :param network_interface_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_INSTANCE_NETWORK_INTERFACE_PATH.format(
                    instance_id=instance_id, network_interface_id=network_interface_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_instance_network_interface(self, region, instance_id, network_interface_id, network_interface_json):
        """

        :param region:
        :param instance_id:
        :param network_interface_id:
        :param network_interface_json:
        :return:
        """
        if not isinstance(network_interface_json, dict):
            raise IBMInvalidRequestError("Parameter 'network_interface_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_INSTANCE_NETWORK_INTERFACE_PATH.format(
                    instance_id=instance_id, network_interface_id=network_interface_id
                )
            ),
            json=network_interface_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_instance_floating_ips(self, region, instance_id, network_interface_id):
        """

        :param region:
        :param instance_id:
        :param network_interface_id:
        :return:
        """

        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=LIST_INSTANCE_FLOATING_IPS_PATH.format(
                    instance_id=instance_id, network_interface_id=network_interface_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("floating_ips", [])

    def delete_instance_floating_ip(self, region, instance_id, network_interface_id, floating_ip_id):
        """

        :param region:
        :param instance_id:
        :param network_interface_id:
        :param floating_ip_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_INSTANCE_FLOATING_IP_PATH.format(
                    instance_id=instance_id, network_interface_id=network_interface_id, floating_ip_id=floating_ip_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_instance_floating_ip(self, region, instance_id, network_interface_id, floating_ip_id):
        """

        :param region:
        :param instance_id:
        :param network_interface_id:
        :param floating_ip_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_INSTANCE_FLOATING_IP_PATH.format(
                    instance_id=instance_id, network_interface_id=network_interface_id, floating_ip_id=floating_ip_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def associate_instance_floating_ip(self, region, instance_id, network_interface_id, floating_ip_id):
        """

        :param region:
        :param instance_id:
        :param network_interface_id:
        :param floating_ip_id:
        :return:
        """
        request = requests.Request(
            "PUT",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_INSTANCE_FLOATING_IP_PATH.format(
                    instance_id=instance_id, network_interface_id=network_interface_id, floating_ip_id=floating_ip_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_instance_volume_attachments(self, region, instance_id):
        """

        :param region:
        :param instance_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_INSTANCE_VOLUME_ATTACHMENTS_PATH.format(instance_id=instance_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("volume_attachments", [])

    def create_instance_volume_attachment(self, region, instance_id, volume_attachment_json):
        """

        :param region:
        :param instance_id:
        :param volume_attachment_json:
        :return:
        """
        if not isinstance(volume_attachment_json, dict):
            raise IBMInvalidRequestError("Parameter 'volume_attachment_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(
                region=region, path=CREATE_INSTANCE_VOLUME_ATTACHMENT_PATH.format(instance_id=instance_id)
            ),
            json=volume_attachment_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_instance_volume_attachment(self, region, instance_id, volume_attachment_id):
        """

        :param region:
        :param instance_id:
        :param volume_attachment_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_INSTANCE_VOLUME_ATTACHMENT_PATH.format(
                    instance_id=instance_id, volume_attachment_id=volume_attachment_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_instance_volume_attachment(self, region, instance_id, volume_attachment_id):
        """

        :param region:
        :param instance_id:
        :param volume_attachment_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_INSTANCE_VOLUME_ATTACHMENT_PATH.format(
                    instance_id=instance_id, volume_attachment_id=volume_attachment_id
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_instance_volume_attachment(self, region, instance_id, volume_attachment_id, volume_attachment_json):
        """

        :param region:
        :param instance_id:
        :param volume_attachment_id:
        :param volume_attachment_json:
        :return:
        """
        if not isinstance(volume_attachment_json, dict):
            raise IBMInvalidRequestError("Parameter 'volume_attachment_json' should be a dictionary")

        # TODO: Create schema for input and validate it

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_INSTANCE_VOLUME_ATTACHMENT_PATH.format(
                    instance_id=instance_id, volume_attachment_id=volume_attachment_id
                )
            ),
            json=volume_attachment_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
