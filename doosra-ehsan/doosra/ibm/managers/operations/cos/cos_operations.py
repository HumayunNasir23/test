import logging

import ibm_boto3
from ibm_botocore.client import Config
from ibm_botocore.exceptions import ClientError

from .consts import COS_AUTH_ENDPOINT, COS_ENDPOINT, DEFAULT_REGION
from .fetch_operations import FetchOperations
from doosra.common.utils import decrypt_api_key

LOGGER = logging.getLogger(__name__)


class COSOperations(object):
    def __init__(self, cloud, region, service_id):
        self.cloud = cloud
        self.region = region or DEFAULT_REGION

        self.cos = ibm_boto3.client(
            "s3", ibm_api_key_id=decrypt_api_key(self.cloud.api_key), ibm_service_instance_id=service_id,
            ibm_auth_endpoint=COS_AUTH_ENDPOINT, config=Config(signature_version="oauth"),
            endpoint_url=COS_ENDPOINT.format(region=self.region))
        self.fetch_ops = FetchOperations(self.cloud, self.region, self.cos)

    def create_bucket(self, bucket_name, region):
        """
        Create cos bucket
        """
        if not bucket_name:
            return
        try:
            response = self.cos.create_bucket(Bucket=bucket_name,
                                              CreateBucketConfiguration={
                                                  'LocationConstraint': region + "-standard"})
            LOGGER.info(f"Bucket creation response : {response}")
            return response
        except ClientError:
            pass

    def delete_items(self, bucket_name, items):
        """
        Delete Items for cos bucket names provided in items: list
        """
        if not bucket_name or not items:
            return
        try:
            delete_request = {"Objects": [{"Key": item} for item in items]}

            response = self.cos.delete_objects(
                Bucket=bucket_name, Delete=delete_request
            )
            return response
        except ClientError:
            pass
