"""
This file contains ICSoftlayerManager, responsible for creating, deleting and getting instances for Image Conversion
"""
from SoftLayer import create_client_from_env
from SoftLayer.managers import VSManager
from SoftLayer.exceptions import SoftLayerAPIError

from .exceptions import SLResourceNotFoundException, SLAuthException, UnexpectedSLError


class ICSoftlayerManager:
    """
    Client for Softlayer VSI creation/deletion/fetching
    """
    def __init__(self):
        self.vs_manager = VSManager(client=create_client_from_env())

    def create_instance(self, instance_dict):
        """
        Create a VSI on Softlayer
        :param instance_dict: <dict>  (preferably from ImageConversionInstance.generate_config_file_contents function)

        :raises SLAuthException if Softlayer credentials are not valid
        :raises UnexpectedSLError if there is an unexpected error from softlayer in its API

        :return: <dict> Dictionary containing VSI details if the call was successful
        """
        try:
            response = self.vs_manager.create_instance(**instance_dict)
        except SoftLayerAPIError as ex:
            if ex.faultString == "Invalid API token.":
                raise SLAuthException()
            else:
                raise UnexpectedSLError(ex)

        return response

    def delete_instance(self, softlayer_instance_id):
        """
        Deletes a VSI from Softlayer
        :param softlayer_instance_id: <int/string> ID of the VSI on softlayer to delete

        :raises SLAuthException if Softlayer credentials are not valid
        :raises SLResourceNotFoundException if the VSI with provided ID does not exist in softlayer
        :raises UnexpectedSLError if there is an unexpected error from softlayer in its API
        """
        try:
            self.vs_manager.cancel_instance(softlayer_instance_id)
        except SoftLayerAPIError as ex:
            if ex.faultCode == "SoftLayer_Exception_ObjectNotFound":
                raise SLResourceNotFoundException(ex.reason)
            elif ex.faultString == "Invalid API token.":
                raise SLAuthException()
            else:
                raise UnexpectedSLError(ex)

    def get_instance(self, softlayer_instance_id):
        """
        Get a VSI's details from Softlayer
        :param softlayer_instance_id: <int/string> ID of the VSI on softlayer to fetch

        :raises SLAuthException if Softlayer credentials are not valid
        :raises SLResourceNotFoundException if the VSI with provided ID does not exist in softlayer
        :raises UnexpectedSLError if there is an unexpected error from softlayer in its API

        :return: <dict> Dictionary containing VSI details if the call was successful
        """
        try:
            instance_data = self.vs_manager.get_instance(softlayer_instance_id)
        except SoftLayerAPIError as ex:
            if ex.faultCode == "SoftLayer_Exception_ObjectNotFound":
                raise SLResourceNotFoundException(ex.reason)
            elif ex.faultString == "Invalid API token.":
                raise SLAuthException()
            else:
                raise UnexpectedSLError(ex)

        return instance_data
