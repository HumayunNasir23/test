from google.auth.exceptions import RefreshError, TransportError, DefaultCredentialsError
from google.oauth2.credentials import Credentials

from doosra.gcp.managers.exceptions import CloudAuthError
from doosra.gcp.managers.operations.compute_engine.compute_engine_operations import ComputeEngineOperations
from doosra.gcp.managers.operations.resource_mangement.resource_management_operations import \
    ResourceManagementOperations
from doosra.models import GcpCloud


class GCPManager(object):
    """
    GCP Manager should be the entry point for all GCP related operations
    """

    def __init__(self, cloud):
        """
        Initialize GCP Manager object
        :param cloud: An object of class GcpCloud
        """
        assert isinstance(cloud, GcpCloud), "Invalid parameter 'cloud': Only GcpCloud type object allowed"

        self.credentials = None
        try:
            if cloud.gcp_credentials:
                self.credentials = Credentials(**cloud.gcp_credentials.to_json())
        except (DefaultCredentialsError, RefreshError, TransportError):
            raise CloudAuthError(cloud.id)

        self.resource_management_operations = ResourceManagementOperations(cloud, self.credentials)
        self.compute_engine_operations = ComputeEngineOperations(cloud, self.credentials)
