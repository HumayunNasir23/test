from SoftLayer import BaseClient
from SoftLayer.exceptions import SoftLayerAPIError
from SoftLayer.managers import ImageManager, VSManager
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from doosra.migration.managers.exceptions import SLAuthError, SLExecuteError, SLRateLimitExceededError
from doosra.migration.managers.operations.consts import BACK_OFF_FACTOR, INVALID_API_KEY_CODE, MAX_INTERVAL, \
    RETRY, SL_RATE_LIMIT_FAULT_CODE


class CreateOperations:
    client: BaseClient
    image_manager: ImageManager
    vs_manager: VSManager

    def __init__(self, client, username):
        self.client = client
        self.username = username
        self.retry = self.requests_retry()

    def requests_retry(self):
        self.retry = Retrying(
            stop=stop_after_attempt(RETRY),
            retry=retry_if_exception_type(SLRateLimitExceededError),
            wait=wait_random_exponential(multiplier=BACK_OFF_FACTOR, max=MAX_INTERVAL),
            reraise=True)
        return self.retry

    def create_instance(self, instance_body):
        """
        Create Sofltlayer Instance
        return:
        """
        try:
            self.vs_manager = VSManager(self.client)
            return self.retry.call(self.vs_manager.create_instance, **instance_body)
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def capture_image(self, instance_id, image_name, additional_disks=False):
        """
        Create and capture image template of an image belonging to classical VSI
        :return:
        """
        try:
            self.vs_manager = VSManager(self.client)
            return self.retry.call(self.vs_manager.capture, instance_id, image_name, additional_disks)
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def export_image(self, image_id, cos_url, api_key):
        """
        Export Image template from Classic to specified COS
        :return:
        """
        try:
            self.image_manager = ImageManager(self.client)
            return self.retry.call(self.image_manager.export_image_to_uri, image_id, cos_url, api_key)
        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def delete_image(self, image_id):
        """
        Delete image template from Classical Infrastructure
        :param image_id: Classical Image ID for the image
        :return:
        """
        try:
            self.image_manager = ImageManager(self.client)
            return self.retry.call(self.image_manager.delete_image, image_id)

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)

    def delete_instance(self, instance_id):
        """
        Delete instance from Classical Infrastructure
        :param instance_id: Classical Instance ID for the image
        :return:
        """
        try:
            self.vs_manager = VSManager(self.client)
            return self.retry.call(self.vs_manager.cancel_instance, instance_id)

        except SoftLayerAPIError as ex:
            if ex.faultCode == SL_RATE_LIMIT_FAULT_CODE:
                raise SLRateLimitExceededError(ex)
            elif ex.faultCode == INVALID_API_KEY_CODE:
                raise SLAuthError(self.username)
            raise SLExecuteError(ex)
