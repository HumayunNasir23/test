import requests
from flask import current_app
from requests import ReadTimeout, RequestException
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

from doosra.common.consts import CREATED
from doosra.ibm.managers.exceptions import IBMConnectError, IBMAuthError, IBMExecuteError
from doosra.models import IBMCredentials, IBMResourceGroup, TransitGateway, TransitGatewayConnection
from doosra.transit_gateway.consts import VERSION, TRANSIT_BASE_URL
from doosra.transit_gateway.manager.operations.patterns import LIST_TRANSIT_GATEWAYS_PATTERN, \
    GET_TRANSIT_GATEWAY_PATTERN, GET_RESOURCE_GROUP_PATTERN, GET_TRANSIT_GATEWAY_CONNECTION_PATTERN, \
    LIST_TRANSIT_GATEWAY_CONNECTIONS_PATTERN, LIST_TRANSIT_LOCATIONS


class FetchOperations(object):
    """
    Define all the listing Operations here for the TransitGateway
    """

    def __init__(self, cloud, iam_ops):
        self.cloud = cloud
        self.base_url = TRANSIT_BASE_URL
        self.session = self.requests_retry_session()
        self.iam_ops = iam_ops

    def requests_retry_session(self, retries=3):
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 503, 504),
            method_whitelist=["GET", "PUT", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount(self.base_url, adapter)
        return self.session

    def get_resource_groups(self, name=None, resource_id=None):
        """
        Manages resources organized in your account.
        :return:
        """
        resource_groups_list = list()
        resource_groups = self.__execute(self.__format_api_url(GET_RESOURCE_GROUP_PATTERN))
        for resource_group in resource_groups.get('resources'):
            ibm_resource_group = IBMResourceGroup(resource_group['name'], resource_group['id'], self.cloud.id)
            if not ((name and name != ibm_resource_group.name) or
                    (resource_id and resource_id != ibm_resource_group.resource_id)):
                resource_groups_list.append(ibm_resource_group)
        return resource_groups_list

    def list_transit_locations(self):
        locations = self.__execute(self.__format_api_url(LIST_TRANSIT_LOCATIONS))

        if locations:
            return locations.get("locations")

    def get_all_transit_gateways(self, name=None, required_relations=True):
        """
        This request lists all Transit gateways. A Transit gateway is a virtual network device associated within Transit Gateway Connection.
        :return:
        """
        transit_gateways_list = list()
        response = self.__execute(self.__format_api_url(LIST_TRANSIT_GATEWAYS_PATTERN))
        if not response.get("transit_gateways"):
            return transit_gateways_list

        for transit_gateway in response.get("transit_gateways"):
            transit_gateway = TransitGateway(
                name=transit_gateway["name"],
                region=transit_gateway["location"],
                status=CREATED,
                gateway_status=transit_gateway["status"],
                crn=transit_gateway["crn"],
                resource_id=transit_gateway["id"],
                created_at=transit_gateway["created_at"],
                is_global_route=transit_gateway["global"],
                cloud_id=self.cloud.id,
            )

            if required_relations:
                connections = self.get_all_transit_gateway_connections(
                    transit_gateway.resource_id
                )
                if connections:
                    transit_gateway.connections = connections

            transit_gateways_list.append(transit_gateway)
        return transit_gateways_list

    def get_all_transit_gateway_connections(self, transit_gateway_id, name=None):
        """
        This request lists all Connections to Specific Transit gateway.
        :return:
        """
        transit_gateway_connection_list = list()
        response = self.__execute(
            self.__format_api_url(
                LIST_TRANSIT_GATEWAY_CONNECTIONS_PATTERN, transit_gateway_id=transit_gateway_id
            )
        )
        if response.get("connections"):
            for connection in response.get("connections"):
                if name and name != connection.get("name"):
                    continue

                transit_gateway_connection = TransitGatewayConnection(
                    name=connection["name"],
                    network_type=connection["network_type"],
                    network_id=connection["network_id"] if connection['network_type'] == "vpc" else None,
                    resource_id=connection["id"],
                    status=CREATED,
                    connection_status=connection["status"],
                    created_at=connection["created_at"],
                )
                transit_gateway_connection_list.append(transit_gateway_connection)

        return transit_gateway_connection_list

    def get_transit_gateway(self, gateway_id):

        transit_gateway = self.__execute(self.__format_api_url(GET_TRANSIT_GATEWAY_PATTERN, gateway_id=gateway_id))

        if not transit_gateway.get('id'):
            return

        transit_gateway_obj = TransitGateway(
            name=transit_gateway["name"],
            region=transit_gateway["location"],
            gateway_status=transit_gateway["status"],
            resource_id=transit_gateway["id"],
            created_at=transit_gateway["created_at"],
            is_global_route=transit_gateway["global"],
            cloud_id=self.cloud.id,
        )

        transit_gateway_obj.connections = self.get_all_transit_gateway_connections(transit_gateway.get('id'))

        return transit_gateway_obj

    def get_transit_gateway_status(self, transit_gateway):
        """
        This request retrieves a single transit gateway specified by the identifier in the URL.
        :return:
        """
        response = self.__execute(
            self.__format_api_url(GET_TRANSIT_GATEWAY_PATTERN, gateway_id=transit_gateway.resource_id)
        )
        return response.get("status")

    def get_transit_gateway_connection(self, connection):

        existing_connection = self.__execute(self.__format_api_url(GET_TRANSIT_GATEWAY_CONNECTION_PATTERN,
                                                                   gateway_id=connection.transit_gateway.resource_id,
                                                                   connection_id=connection.resource_id))
        if not existing_connection.get('id'):
            return

        tg_connection = TransitGatewayConnection(
            name=existing_connection["name"],
            connection_status=existing_connection['status'],
            network_type=existing_connection["network_type"],
            network_id=existing_connection["network_id"] if connection.network_type == "vpc" else None,
            resource_id=existing_connection["id"],
            created_at=existing_connection["created_at"],
        )

        return tg_connection

    def get_transit_gateway_connection_status(self, connection):
        """
        This request retrieves a single transit gateway connection specified by the identifier in the URL.
        :return:
        """
        response = self.__execute(
            self.__format_api_url(GET_TRANSIT_GATEWAY_CONNECTION_PATTERN,
                                  gateway_id=connection.transit_gateway.resource_id,
                                  connection_id=connection.resource_id)
        )

        return response.get("status")

    @staticmethod
    def __format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the unformatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def __execute(self, request, data=None):
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)
        try:
            request_url = request[1].format(base_url=self.base_url, version=VERSION)
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(
                    IBMCredentials(self.iam_ops.authenticate_cloud_account())
                )

            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.debug("{0} : {1}".format(request[0], request_url))
            response = self.session.request(
                request[0], request_url, data=data, timeout=30, headers=headers
            )
        except (
                ConnectionError,
                ReadTimeout,
                RequestException,
                MaxRetryError,
                ReadTimeoutError,
        ) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id)
        else:
            if response.status_code == 401:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code in [400, 408, 500]:
                raise IBMExecuteError(response)
            elif response.status_code not in [200, 201, 204, 404]:
                raise IBMExecuteError(response)
            try:
                return response.json()
            except:
                return response
