"""
Base client to inherit for all the clients
"""
import logging

import requests
from requests.exceptions import ConnectionError, ReadTimeout, RequestException

from doosra import db as doosradb
from doosra.common.utils import decrypt_api_key
from doosra.models import IBMCloud
from .consts import VPC_RESOURCE_REQUIRED_PARAMS, VSI_FIXED_DATE_BASED_VERSION
from .exceptions import IBMAuthError, IBMConnectError, IBMExecuteError, IBMInvalidRequestError
from .session_context import get_requests_session
from .urls import AUTH_URL

LOGGER = logging.getLogger(__name__)


class BaseClient:
    """
    Parent Class for all of the clients
    """
    def __init__(self, cloud_id):
        self.cloud_id = cloud_id

    def authenticate_cloud_account(self, api_key):
        """
        Authenticate IBM Cloud account and return IAM token
        :return:
        """
        req = requests.Request(
            "POST",
            AUTH_URL,
            params={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": api_key,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
        )
        return self._execute_request(req, "AUTH")

    def _paginate_resource(self, request, request_type, resource):
        resource_list = []

        response = self._execute_request(request, request_type)
        resource_list.extend(response.get(resource, []))

        while 'next' in response:
            request.url = response['next']['href']
            response = self._execute_request(request, request_type)
            resource_list.extend(response.get(resource, []))

        return {resource: resource_list}

    def _execute_request(self, request, request_type, updated_api_version=False):
        try:
            return self.__execute_request(request, request_type, updated_api_version, False)
        except IBMAuthError:
            return self.__execute_request(request, request_type, updated_api_version, True)

    def __execute_request(self, request, request_type, updated_api_version, force_auth):
        assert request_type in ["AUTH", "VPC_RESOURCE", "RESOURCE_GROUP", "K8S_RESOURCE", "K8S_KUBE_CONFIG"]
        assert isinstance(request, requests.Request)

        auth_resp = None

        cloud = doosradb.session.query(IBMCloud).get(self.cloud_id)
        if not cloud:
            raise IBMInvalidRequestError("Cloud not found")

        auth_required = cloud.auth_required or force_auth
        api_key = decrypt_api_key(cloud.api_key)
        access_token = cloud.credentials.access_token
        doosradb.session.commit()

        if request_type in ["VPC_RESOURCE", "RESOURCE_GROUP", "K8S_RESOURCE", "K8S_KUBE_CONFIG"]:
            if auth_required:
                LOGGER.info("Authenticating Cloud {}".format(self.cloud_id))
                auth_resp = self.authenticate_cloud_account(api_key)
                access_token = " ".join([auth_resp.get("token_type"), auth_resp.get("access_token")])

            if request_type == "VPC_RESOURCE":
                if updated_api_version:
                    VPC_RESOURCE_REQUIRED_PARAMS["version"] = VSI_FIXED_DATE_BASED_VERSION
                if request.params:
                    request.params.update(VPC_RESOURCE_REQUIRED_PARAMS)
                else:
                    request.params = VPC_RESOURCE_REQUIRED_PARAMS

            if request.headers:
                request.headers.update({"Authorization": access_token})
            else:
                request.headers = {"Authorization": access_token}

        if auth_resp:
            cloud.update_from_auth_response(auth_resp)
            doosradb.session.commit()

        try:
            with get_requests_session() as req_session:
                request = req_session.prepare_request(request)
                response = req_session.send(request, timeout=30)
        except (ConnectionError, ReadTimeout, RequestException):
            raise IBMConnectError(self.cloud_id)

        if response.status_code == 401:
            raise IBMAuthError(self.cloud_id)
        elif response.status_code in [400, 403, 404, 408, 409]:
            raise IBMExecuteError(response)
        elif response.status_code not in [200, 201, 204]:
            raise IBMExecuteError(response)

        try:
            response_json = response.json()
        except Exception:
            response_json = {}
        return response_json
