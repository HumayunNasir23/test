from google.auth.exceptions import RefreshError, TransportError, DefaultCredentialsError
from googleapiclient.errors import HttpError, UnexpectedBodyError, UnexpectedMethodError

from doosra.gcp.managers.exceptions import *
from doosra.models.gcp_models import GcpCloudProject


class FetchOperations(object):
    def __init__(self, cloud, service):
        self.cloud = cloud
        self.service = service

    def get_cloud_projects(self, name=None):
        """
        Get all GCP projects for the specified user account
        :return:
        """
        cloud_projects = list()
        request = self.service.projects().list()
        while request is not None:
            response = self.execute(request)
            for project in response.get('projects', []):
                if name and name != project.get('name'):
                    continue

                cloud_projects.append(GcpCloudProject(project.get('name'), project.get('projectId'), self.cloud.id))
            request = self.service.projects().list_next(previous_request=request, previous_response=response)

        return cloud_projects

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
