import SoftLayer

from doosra.common.utils import decrypt_api_key
from doosra.migration.managers.operations.create_operations import CreateOperations
from doosra.migration.managers.operations.fetch_operations import FetchOperations


class SoftLayerManager:
    username: str
    api_key: str
    fetch_ops: FetchOperations

    def __init__(self, username: str, api_key: str):
        assert (username and api_key), "'SoftLayerManager' must have username and api_key"

        self.username = username
        self.api_key = decrypt_api_key(api_key)
        self.client = SoftLayer.create_client_from_env(self.username, self.api_key)
        self.fetch_ops = FetchOperations(self.client, self.username)
        self.create_ops = CreateOperations(self.client, self.username)
