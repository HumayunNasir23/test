"""
This file contains Client for VPN related APIs
"""
import requests

from .paths import LIST_IKE_POLICIES, CREATE_IKE_POLICY, DELETE_IKE_POLICY, GET_IKE_POLICY, UPDATE_IKE_POLICY, \
    LIST_CONNECTION_USING_SPECIFIED_IKE_POLICY, LIST_IPSEC_POLICIES, CREATE_IPSEC_POLICY, DELETE_IPSEC_POLICY, \
    GET_IPSEC_POLICY, UPDATE_IPSEC_POLICY, LIST_CONNECTION_USING_SPECIFIED_IPSEC_POLICY, LIST_VPN_GATEWAYS, \
    CREATE_VPN_GATEWAYS, DELETE_VPN_GATEWAYS, GET_VPN_GATEWAYS, UPDATE_VPN_GATEWAY, LIST_CONNECTIONS_OF_VPN_GATEWAY, \
    CREATE_VPN_CONNECTION, DELETE_VPN_CONNECTION, GET_VPN_CONNECTION, UPDATE_VPN_CONNECTION, LIST_LOCAL_CIDR, \
    REMOVE_LOCAL_CIDR, CHECK_SPECIFIC_LOCAL_CIDR_EXISTS, SET_LOCAL_CIDR, LIST_PEER_CIDR, REMOVE_PEER_CIDR, \
    CHECK_SPECIFIC_PEER_CIDR_EXISTS, SET_PEER_CIDR
from ..base_client import BaseClient
from ..consts import VPC_DEFAULT_PAGINATION_LIMIT
from ..urls import VPC_URL_TEMPLATE


class VPNsClient(BaseClient):
    """
    Client for VPN related APIs
    """

    def __init__(self, cloud_id):
        super(VPNsClient, self).__init__(cloud_id)

    def list_ike_policies(self, region, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {
            "limit": limit
        }
        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_IKE_POLICIES), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "ike_policies")

        return response["ike_policies"]

    def create_ike_policy(self, region, ike_policy_json):
        """

        :param region:
        :param ike_policy_json:
        :return:
        """
        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_IKE_POLICY), json=ike_policy_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_ike_policy(self, region, ike_policy_id):
        """

        :param region:
        :param ike_policy_id:
        :return:
        """
        request = requests.Request(
            "DELETE", VPC_URL_TEMPLATE.format(region=region, path=DELETE_IKE_POLICY.format(ike_policy_id=ike_policy_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_ike_policy(self, region, ike_policy_id):
        """

        :param region:
        :param ike_policy_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_IKE_POLICY.format(ike_policy_id=ike_policy_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_ike_policy(self, region, ike_policy_id, ike_policy_json):
        """

        :param region:
        :param ike_policy_id:
        :param ike_policy_json:
        :return:
        """
        # TODO use schema to check payload

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(region=region, path=UPDATE_IKE_POLICY.format(ike_policy_id=ike_policy_id)),
            json=ike_policy_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_conn_using_specified_ike_policy(self, region, ike_policy_id):
        """

        :param region:
        :param ike_policy_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_CONNECTION_USING_SPECIFIED_IKE_POLICY.format(ike_policy_id=ike_policy_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_ipsec_policies(self, region, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param limit: Number of Resources Per Page
        :return:
        """

        params = {
            "limit": limit
        }

        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_IPSEC_POLICIES), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "ipsec_policies")

        return response["ipsec_policies"]

    def create_ipsec_policy(self, region, ipsec_policy_json):
        """

        :param region:
        :param ipsec_policy_json:
        :return:
        """
        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_IPSEC_POLICY), json=ipsec_policy_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_ipsec_policy(self, region, ipsec_policy_id):
        """

        :param region:
        :param ipsec_policy_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(region=region, path=DELETE_IPSEC_POLICY.format(ipsec_policy_id=ipsec_policy_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_ipsec_policy(self, region, ipsec_policy_id):
        """

        :param region:
        :param ipsec_policy_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_IPSEC_POLICY.format(ipsec_policy_id=ipsec_policy_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_ipsec_policy(self, region, ipsec_policy_id, ipsec_policy_json):
        """

        :param region:
        :param ipsec_policy_id:
        :param ipsec_policy_json:
        :return:
        """
        # TODO use schema to check payload

        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(region=region, path=UPDATE_IPSEC_POLICY.format(ipsec_policy_id=ipsec_policy_id)),
            json=ipsec_policy_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_conn_using_specified_ipsec_policy(self, region, ipsec_policy_id):
        """

        :param region:
        :param ipsec_policy_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_CONNECTION_USING_SPECIFIED_IPSEC_POLICY.format(ipsec_policy_id=ipsec_policy_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_vpn_gateways(self, region, resource_id=None, limit=VPC_DEFAULT_PAGINATION_LIMIT):
        """

        :param region:
        :param resource_id:
        :param limit: Number of Resources Per Page
        :return:
        """
        params = {"resource.id": resource_id, "limit": limit}

        request = requests.Request("GET", VPC_URL_TEMPLATE.format(region=region, path=LIST_VPN_GATEWAYS), params=params)

        response = self._paginate_resource(request, "VPC_RESOURCE", "vpn_gateways")

        return response["vpn_gateways"]

    def create_vpn_gateway(self, region, vpn_gateway_json):
        """

        :param region:
        :param vpn_gateway_json:
        :return:
        """
        # TODO use schema to check payload

        request = requests.Request(
            "POST", VPC_URL_TEMPLATE.format(region=region, path=CREATE_VPN_GATEWAYS), json=vpn_gateway_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_vpn_gateway(self, region, vpn_gateway_id):
        """

        :param region:
        :param vpn_gateway_id:
        :return:
        """
        request = requests.Request(
            "DELETE", VPC_URL_TEMPLATE.format(region=region, path=DELETE_VPN_GATEWAYS.format(vpn_gateway_id=vpn_gateway_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_vpn_gateway(self, region, vpn_gateway_id):
        """

        :param region:
        :param vpn_gateway_id:
        :return:
        """
        request = requests.Request(
            "GET", VPC_URL_TEMPLATE.format(region=region, path=GET_VPN_GATEWAYS.format(vpn_gateway_id=vpn_gateway_id))
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_vpn_gateway(self, region, vpn_gateway_id, vpn_gateway_json):
        """

        :param region:
        :param vpn_gateway_id:
        :param vpn_gateway_json:
        :return:
        """
        # TODO use schema to check payload
        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(region=region, path=UPDATE_VPN_GATEWAY.format(vpn_gateway_id=vpn_gateway_id)),
            json=vpn_gateway_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_vpn_gateway_connections(self, region, vpn_gateway_id, status=None):
        """

        :param region:
        :param vpn_gateway_id:
        :param status:
        :return:
        """
        params = {"status": status}

        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_CONNECTIONS_OF_VPN_GATEWAY.format(vpn_gateway_id=vpn_gateway_id)
            ),
            params=params
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("connections", [])

    def create_vpn_connection(self, region, vpn_gateway_id, connection_json):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_json:
        :return:
        """
        # TODO use schema to check payload

        request = requests.Request(
            "POST",
            VPC_URL_TEMPLATE.format(region=region, path=CREATE_VPN_CONNECTION.format(vpn_gateway_id=vpn_gateway_id)),
            json=connection_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def delete_vpn_connection(self, region, vpn_gateway_id, connection_id):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=DELETE_VPN_CONNECTION.format(vpn_gateway_id=vpn_gateway_id, connection_id=connection_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def get_vpn_connection(self, region, vpn_gateway_id, connection_id):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=GET_VPN_CONNECTION.format(vpn_gateway_id=vpn_gateway_id, connection_id=connection_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def update_vpn_connection(self, region, vpn_gateway_id, connection_id, vpn_connection_json):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :param vpn_connection_json:
        :return:
        """
        # TODO use schema to check payload
        request = requests.Request(
            "PATCH",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=UPDATE_VPN_CONNECTION.format(vpn_gateway_id=vpn_gateway_id, connection_id=connection_id)
            ),
            json=vpn_connection_json
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_local_cidrs(self, region, vpn_gateway_id, connection_id):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_LOCAL_CIDR.format(vpn_gateway_id=vpn_gateway_id, connection_id=connection_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("local_cidrs", [])

    def remove_local_cidr(self, region, vpn_gateway_id, connection_id, prefix_address, prefix_length):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :param prefix_address:
        :param prefix_length:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=REMOVE_LOCAL_CIDR.format(
                    vpn_gateway_id=vpn_gateway_id,
                    connection_id=connection_id,
                    prefix_address=prefix_address,
                    prefix_length=prefix_length
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def check_specific_local_cidr(self, region, vpn_gateway_id, connection_id, prefix_address, prefix_length):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :param prefix_address:
        :param prefix_length:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=CHECK_SPECIFIC_LOCAL_CIDR_EXISTS.format(
                    vpn_gateway_id=vpn_gateway_id,
                    connection_id=connection_id,
                    prefix_address=prefix_address,
                    prefix_length=prefix_length
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def set_local_cidr(self, region, vpn_gateway_id, connection_id, prefix_address, prefix_length):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :param prefix_address:
        :param prefix_length:
        :return:
        """
        request = requests.Request(
            "PUT",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=SET_LOCAL_CIDR.format(
                    vpn_gateway_id=vpn_gateway_id,
                    connection_id=connection_id,
                    prefix_address=prefix_address,
                    prefix_length=prefix_length
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def list_peer_cidr(self, region, vpn_gateway_id, connection_id):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region, path=LIST_PEER_CIDR.format(vpn_gateway_id=vpn_gateway_id, connection_id=connection_id)
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response.get("peer_cidrs", [])

    def remove_peer_cidr(self, region, vpn_gateway_id, connection_id, prefix_address, prefix_length):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :param prefix_address:
        :param prefix_length:
        :return:
        """
        request = requests.Request(
            "DELETE",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=REMOVE_PEER_CIDR.format(
                    vpn_gateway_id=vpn_gateway_id,
                    connection_id=connection_id,
                    prefix_address=prefix_address,
                    prefix_length=prefix_length
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def check_specific_peer_cidr(self, region, vpn_gateway_id, connection_id, prefix_address, prefix_length):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :param prefix_address:
        :param prefix_length:
        :return:
        """
        request = requests.Request(
            "GET",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=CHECK_SPECIFIC_PEER_CIDR_EXISTS.format(
                    vpn_gateway_id=vpn_gateway_id,
                    connection_id=connection_id,
                    prefix_address=prefix_address,
                    prefix_length=prefix_length
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response

    def set_peer_cidr(self, region, vpn_gateway_id, connection_id, prefix_address, prefix_length):
        """

        :param region:
        :param vpn_gateway_id:
        :param connection_id:
        :param prefix_address:
        :param prefix_length:
        :return:
        """
        request = requests.Request(
            "PUT",
            VPC_URL_TEMPLATE.format(
                region=region,
                path=SET_PEER_CIDR.format(
                    vpn_gateway_id=vpn_gateway_id,
                    connection_id=connection_id,
                    prefix_address=prefix_address,
                    prefix_length=prefix_length
                )
            )
        )

        response = self._execute_request(request, "VPC_RESOURCE")

        return response
