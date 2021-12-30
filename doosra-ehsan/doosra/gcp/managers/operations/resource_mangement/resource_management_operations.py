from google.auth.exceptions import RefreshError, TransportError, DefaultCredentialsError
from googleapiclient import discovery
from googleapiclient.errors import HttpError, UnexpectedBodyError, UnexpectedMethodError

from doosra.gcp.managers.consts import RESOURCE_MANAGER_SERVICE_NAME
from doosra.gcp.managers.exceptions import *
from .fetch_operations import FetchOperations


class ResourceManagementOperations(object):
    def __init__(self, cloud, credentials):
        self.cloud = cloud
        self.credentials = credentials
        self.service = discovery.build(RESOURCE_MANAGER_SERVICE_NAME, 'v1', credentials=self.credentials,
                                       cache_discovery=False)
        self.fetch_ops = FetchOperations(self.cloud, self.service)

    def create_cloud_project(self, project):
        """
        Create a new GCP project
        :param project:
        :return:
        """
        request = self.service.projects().create(body=project.to_json_body())
        self.execute(request)

    def execute(self, request):
        """
        Executes request object on GCP cloud account and returns the response.
        :param request:
        :return:
        """
        try:
            response = request.execute()
        except (DefaultCredentialsError, HttpError, UnexpectedBodyError, UnexpectedMethodError, RefreshError,
                TransportError) as ex:
            if isinstance(ex, (UnexpectedBodyError, UnexpectedMethodError)):
                raise CloudInvalidRequestError(self.cloud.id)
            elif isinstance(ex, HttpError):
                raise CloudExecuteError(ex)
            elif isinstance(ex, (RefreshError, DefaultCredentialsError, TransportError)):
                raise CloudAuthError(self.cloud.id)
        else:
            return response
