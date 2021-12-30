import requests
from flask import current_app
from requests.exceptions import ConnectionError, ReadTimeout, RequestException
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

from doosra.ibm.managers.exceptions import *
from doosra.transit_gateway.consts import VERSION, TRANSIT_BASE_URL
from doosra.transit_gateway.manager.operations.patterns import *
from doosra.models import IBMCredentials


class RawFetchOperations(object):
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

    def get_all_transit_gateways(self, name=None):
        """
        Fetch all Transit gateways available in the region.
        :return:
        """
        response = self.execute(self.format_api_url(LIST_TRANSIT_GATEWAYS_PATTERN))
        transit_gateways = response.get("transit_gateways")
        if not transit_gateways:
            return []
        return [
            {
                "name": transit_gateway["name"],
                "id": transit_gateway["id"],
                "region": transit_gateway["location"],
                "created_at": transit_gateway["created_at"],
                "gateway_status": transit_gateway["status"],
                "crn": transit_gateway["crn"],
                "resource_group_id": transit_gateway["resource_group"]["id"] if transit_gateway.get(
                    "resource_group") else None,
                "is_global_route":transit_gateway["global"]
            }
            for transit_gateway in transit_gateways
        ]

    def get_all_transit_gateway_connections(self, transit_gateway_id, name=None):
        """
        Fetch all Connections specific to a Transit gateway available in the region.
        :return:
        """
        response = self.execute(
            self.format_api_url(
                LIST_TRANSIT_GATEWAY_CONNECTIONS_PATTERN, transit_gateway_id=transit_gateway_id
            )
        )
        transit_gateway_connections = response.get("connections")
        if not transit_gateway_connections:
            return []
        return [
            {
                "name": connection["name"],
                "network_id": connection["network_id"] if connection["network_type"] == "vpc" else None,
                "network_type": connection["network_type"],
                "id": connection["id"],
                "created_at": connection["created_at"],
                "connection_status": connection["status"],
            }
            for connection in transit_gateway_connections
        ]

    @staticmethod
    def format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the unformatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def execute(self, request, data=None):
        request_url = request[1].format(
            base_url=self.base_url, version=VERSION
        )
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)
        try:
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(
                    IBMCredentials(self.iam_ops.authenticate_cloud_account())
                )
            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.debug("{0} : {1}".format(request[0], request_url))
            response = self.session.request(
                request[0], request_url, data=data, timeout=50, headers=headers
            )
        except (ConnectionError, ReadTimeout, RequestException, MaxRetryError, ReadTimeoutError) as ex:
            current_app.logger.debug(ex)
            raise IBMConnectError(self.cloud.id, request_url)
        else:
            if response.status_code in [401, 403]:
                raise IBMAuthError(self.cloud.id)
            elif response.status_code in [400, 408, 500]:
                raise IBMExecuteError(response)
            elif response.status_code == 409:
                raise IBMInvalidRequestError(response)
            elif response.status_code not in [200, 201, 204, 404]:
                raise IBMExecuteError(response)
            return response.json()
