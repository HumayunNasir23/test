import json
import time

import requests
from flask import current_app
from requests import ReadTimeout, RequestException
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

from doosra.ibm.managers.exceptions import IBMConnectError, IBMAuthError, IBMExecuteError, IBMInvalidRequestError
from doosra.models import IBMCredentials, TransitGateway, TransitGatewayConnection
from doosra.transit_gateway.consts import VERSION, TRANSIT_BASE_URL
from doosra.transit_gateway.manager.operations.consts import *
from doosra.transit_gateway.manager.operations.fetch_operations import FetchOperations
from doosra.transit_gateway.manager.operations.raw_fetch_operations import RawFetchOperations
from doosra.transit_gateway.manager.operations.patterns import DELETE_TRANSIT_GATEWAY_PATTERN, \
    DELETE_TRANSIT_GATEWAY_CONNECTION_PATTERN, UPDATE_TRANSIT_GATEWAY_PATTERN, \
    UPDATE_TRANSIT_GATEWAY_CONNECTION_PATTERN, CREATE_TRANSIT_GATEWAY_PATTERN, CREATE_TRANSIT_GATEWAY_CONNECTION_PATTERN


class PushOperations(object):
    """
    Define all the CREATE, UPDATE and DELETE Operations for TransitGateway
    """

    def __init__(self, cloud, iam_ops, resource_ops):
        self.cloud = cloud
        self.iam_ops = iam_ops
        self.base_url = TRANSIT_BASE_URL
        self.session = self.requests_retry_session()
        self.resource_ops = resource_ops
        self.fetch_ops = FetchOperations(self.cloud, self.iam_ops)
        self.raw_fetch_ops = RawFetchOperations(self.cloud, self.iam_ops)

    def fetch_obj_status_method_mapper(self, obj):
        func_map = {
            TransitGateway: self.fetch_ops.get_transit_gateway_status,
            TransitGatewayConnection: self.fetch_ops.get_transit_gateway_connection_status
        }

        if func_map.get(obj.__class__):
            return func_map[obj.__class__]

    def create_transit_gateway(self, transit_gateway_obj):
        """
        This request creates a new Transit gateway from a Transit gateway template
        :return:
        """
        response = self.__execute(
            transit_gateway_obj, self.format_api_url(CREATE_TRANSIT_GATEWAY_PATTERN),
            data=transit_gateway_obj.to_json_body())
        return response

    def create_transit_gateway_connection(self, connection_obj, transit_gateway_obj):
        """
        This request creates a Transit Gateway Connection for a Specific Transit Gateway.
        :param connection_obj:
        :param transit_gateway_obj:
        :return:
        """
        response = self.__execute(
            connection_obj,
            self.format_api_url(CREATE_TRANSIT_GATEWAY_CONNECTION_PATTERN,
                                transit_gateway_id=transit_gateway_obj.resource_id),
            data=connection_obj.to_json_body())

        return response

    def delete_transit_gateway(self, transit_gateway):
        response = self.__execute(transit_gateway, self.format_api_url(DELETE_TRANSIT_GATEWAY_PATTERN,
                                                                       gateway_id=transit_gateway.resource_id))
        return response

    def delete_transit_gateway_connection(self, tg_connection):
        response = self.__execute(tg_connection,
                                  self.format_api_url(DELETE_TRANSIT_GATEWAY_CONNECTION_PATTERN,
                                                      gateway_id=tg_connection.transit_gateway.resource_id,
                                                      connection_id=tg_connection.resource_id))
        return response

    def update_transit_gateway(self, transit_gateway):
        response = self.__execute(transit_gateway,
                                  self.format_api_url(UPDATE_TRANSIT_GATEWAY_PATTERN,
                                                      gateway_id=transit_gateway.resource_id),
                                  data=transit_gateway.to_json_body())
        return response

    def update_transit_gateway_connection(self, tg_connection):
        response = self.__execute(tg_connection,
                                  self.format_api_url(UPDATE_TRANSIT_GATEWAY_CONNECTION_PATTERN,
                                                      gateway_id=tg_connection.transit_gateway.resource_id,
                                                      connection_id=tg_connection.resource_id),
                                  data=tg_connection.to_json_body())
        return response

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

    @staticmethod
    def format_api_url(pattern, **kwargs):
        """Format api pattern with key value arguments and skip the unformatted ones"""
        return pattern[0], pattern[1].format(**kwargs)

    def wait_for_operation(self, obj, resource_id, required_status=None):
        """
        Poll for the resource creation or deletion operation and do so while it is completed/deleted
        :return:
        """
        obj_fetch_conf = self.fetch_obj_status_method_mapper(obj)
        if obj_fetch_conf and not resource_id:
            return

        if obj_fetch_conf:
            while True:
                status = obj_fetch_conf(obj)
                if not status:
                    break

                if required_status and required_status == status:
                    return True

                elif status == FAILED:
                    return

                elif status == AVAILABLE or status == ATTACHED:
                    return True

                time.sleep(3)

        return True

    def __execute(self, obj, request, data=None, required_status=None):
        if not self.cloud.credentials:
            raise IBMAuthError(self.cloud.id)
        try:
            request_url = request[1].format(base_url=self.base_url, version=VERSION)
            if self.cloud.credentials.is_token_expired():
                self.cloud.credentials.update_token(IBMCredentials(self.iam_ops.authenticate_cloud_account()))

            headers = {"Authorization": self.cloud.credentials.access_token}
            current_app.logger.debug("{0} : {1}".format(request[0], request_url))
            response = self.session.request(
                request[0], request_url, json=data, timeout=30, headers=headers
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

            if not request[0] == "PATCH":
                status = self.wait_for_operation(obj, obj.resource_id or response.json().get("id"), required_status)
                if not status:
                    raise IBMInvalidRequestError(
                        "The requested operation could not be performed:\n{0} : {1}".format(request[0], request_url))

            return response.json() if response.text else ""
