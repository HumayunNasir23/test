from ibm_botocore.client import ClientError
from requests.exceptions import ReadTimeout
from urllib3.exceptions import ReadTimeoutError

from doosra.common.consts import QCOW2, COS_FILE_EXTENSIONS
from doosra.ibm.managers.exceptions import *


class FetchOperations(object):
    def __init__(self, cloud, region, cos):
        self.cloud = cloud
        self.region = region
        self.cos = cos

    def get_buckets(self, image_type=None, name=None, image_template=None, get_objects=False, primary_objects=True):
        """
        Get a list of available storage buckets in a region
        :return:
        """
        buckets_list = list()
        try:
            buckets = self.cos.list_buckets()
            if not buckets.get("Buckets"):
                return buckets_list

            for bucket in buckets["Buckets"]:
                region = self.get_bucket_location(bucket["Name"])
                if not region:
                    continue

                if name and name != bucket["Name"]:
                    continue

                if get_objects:
                    objects = self.get_bucket_objects(bucket["Name"], primary_objects=primary_objects)

                    if image_type == QCOW2:
                        objects = [
                            object
                            for object in objects
                            if object.split(".")[-1] == image_type
                        ]

                    if image_template and image_template not in objects:
                        continue

                    buckets_list.append(
                        {"name": bucket["Name"], "region": self.region, "objects": objects}
                    )
                else:
                    buckets_list.append(
                        {"name": bucket["Name"], "region": self.region}
                    )

        except ClientError as ex:
            raise IBMInvalidRequestError(ex)

        return buckets_list

    def get_bucket_location(self, bucket_name):
        """
        Get Regional Location for Bucket
        :return:
        """
        try:
            location = self.cos.head_bucket(Bucket=bucket_name)
        except ClientError as ex:
            pass
        else:
            return location

    def get_bucket_objects(self, bucket_name, primary_objects=True):
        try:
            """Get a list of items in a bucket"""
            objects_list = list()
            objects = self.cos.list_objects(Bucket=bucket_name)
            if not objects.get("Contents"):
                return objects_list

            for object in objects["Contents"]:
                object_key = object["Key"]
                if object_key:
                    extension = object_key.split(".")[-1]
                    if primary_objects and (object_key.endswith("0.vhd") or
                                            object_key.endswith("qcow2") or object_key.endswith("vmdk")):
                        objects_list.append(object_key)
                    elif not primary_objects and extension in COS_FILE_EXTENSIONS:
                        objects_list.append(object_key)

            return objects_list
        except (ReadTimeout, ReadTimeoutError) as ex:
            raise IBMBoto3ReadTimeoutError(ex)
