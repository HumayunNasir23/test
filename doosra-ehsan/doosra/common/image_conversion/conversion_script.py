"""
This file hosts all of the image conversion operations
"""
import argparse
import json
import os
import subprocess
import sys
import time

import ibm_boto3
import requests
from ibm_boto3.s3.transfer import TransferConfig, TransferManager
from ibm_botocore.client import Config


class ConversionOperationException(Exception):
    """
    Raised when the conversion operation fails at any step
    """

    def __init__(self, step, error):
        self.msg = "STEP: {}\nERROR: {}".format(step, error)
        super(ConversionOperationException, self).__init__(self.msg)

    def __str__(self):
        return self.msg


class ImageConversionManager(object):
    """
    This class hosts all of the operations for image conversion.

    Requires a config file named 'config.json' to run
    Following keys MUST (REQUIRED) be set in the config file for the class to work:
        VHD_IMAGE_NAME (source image name)
        IBM_API_KEY_ID (ibm cloud api key from IAM)
        IAM_SERVICE_ID (resource_instance_id)
        S3_ENDPOINT (s3 endpoint of cos bucket to download from)
        BUCKET_NAME (bucket name to download from)

    Following keys CAN (OPTIONAL) be set in the config file for the class:
        DOWNLOAD_PATH (Path to download image to)
        CONVERT_PATH (Path to put converted image in)

    :raises ConversionOperationException
    """
    SUPPORTED_SRC_TO_DEST_FORMATS = {
        "vpc": ["qcow2"],
        "vmdk": ["qcow2"]
    }
    SUPPORTED_SRC_FORMATS = list(SUPPORTED_SRC_TO_DEST_FORMATS.keys())
    SUPPORTED_DEST_FORMATS = ["qcow2"]

    def __init__(self):
        try:
            with open(os.path.join(sys.path[0], "config.json")) as config_file:
                config_json = json.loads(config_file.read())
        except IOError:
            raise ConversionOperationException("INIT", "Config file not found")
        except json.JSONDecodeError:
            raise ConversionOperationException("INIT", "Malformed config file")

        for required in [
            "IMAGE_FILE_NAME", "DESTINATION_IMAGE_FORMAT", "IBM_API_KEY_ID", "IAM_SERVICE_ID", "S3_ENDPOINT",
            "BUCKET_NAME"
        ]:
            if required not in config_json:
                raise ConversionOperationException("INIT", "Required key {} not found in config file".format(required))

        self.bucket_name = config_json["BUCKET_NAME"]
        self.image_file_name = config_json["IMAGE_FILE_NAME"]

        self.source_image_format = None

        if config_json["DESTINATION_IMAGE_FORMAT"] not in self.SUPPORTED_DEST_FORMATS:
            raise ConversionOperationException(
                "INIT", "Conversion to {} format not supported".format(config_json["DESTINATION_IMAGE_FORMAT"])
            )
        self.destination_image_format = config_json["DESTINATION_IMAGE_FORMAT"]

        self.converted_image_name = self.clear_extension(self.image_file_name) + "." + self.destination_image_format

        self.image_path_download = config_json.get("DOWNLOAD_PATH") or './'
        if self.image_path_download[-1] != "/":
            self.image_path_download += "/"

        self.image_path_convert = config_json.get("CONVERT_PATH") or './'
        if self.image_path_convert[-1] != "/":
            self.image_path_convert += "/"

        client = ibm_boto3.client(
            service_name='s3', ibm_api_key_id=config_json["IBM_API_KEY_ID"],
            ibm_service_instance_id=config_json["IAM_SERVICE_ID"],
            ibm_auth_endpoint="https://iam.cloud.ibm.com/identity/token",
            config=Config(signature_version="oauth"),
            endpoint_url=config_json["S3_ENDPOINT"])

        self.transfer_manager = TransferManager(client, TransferConfig())

    def download_image(self):
        """
        Download image from COS Bucket
        :raises ConversionOperationException in case download fails
        """
        try:
            future = self.transfer_manager.download(
                self.bucket_name, self.image_file_name, self.image_path_download + self.image_file_name
            )
            future.result()
        except Exception as ex:
            # Catching general exception due to bad documentation of the package
            raise ConversionOperationException("DOWNLOAD", ex)

    def convert_image(self):
        """
        Convert the downloaded VHD Image to QCOW2 format
        :raises ConversionOperationException in case conversion fails
        """
        return_code, output, error = self.__exec_local_cmd(
            "qemu-img info {}".format(self.image_path_download + self.image_file_name)
        )
        if return_code:
            raise ConversionOperationException("CONVERT", error)

        if not output:
            raise ConversionOperationException("CONVERT", "Could not fetch image format")

        source_image_format = None
        for line in output.split("\n"):
            if "file format" not in line.lower():
                continue

            source_image_format = line.split()[-1]
            break

        if not source_image_format:
            raise ConversionOperationException("CONVERT", "Could not find image format")

        if source_image_format not in self.SUPPORTED_SRC_FORMATS:
            raise ConversionOperationException(
                "CONVERT", "Conversion for type {} not supported".format(source_image_format)
            )
        self.source_image_format = source_image_format

        if self.destination_image_format not in self.SUPPORTED_SRC_TO_DEST_FORMATS[self.source_image_format]:
            raise ConversionOperationException(
                "CONVERT", "Conversion from type {} to {} not supported".format(
                    self.source_image_format, self.destination_image_format
                )
            )

        return_code, output, error = self.__exec_local_cmd(
            "qemu-img convert -f {source_type} {source_file} -O {dest_type} {dest_file} -p".format(
                source_type=self.source_image_format, source_file=self.image_path_download + self.image_file_name,
                dest_type=self.destination_image_format,
                dest_file=self.image_path_convert + self.converted_image_name))
        if return_code:
            raise ConversionOperationException("CONVERT", error)

        return_code, output, error = self.__exec_local_cmd(
            "qemu-img resize {source_file} 100G".format(
                source_file=self.image_path_convert + self.converted_image_name))
        if return_code and self.need_resizing(
                image_name=self.image_path_convert + self.converted_image_name):
            raise ConversionOperationException("CONVERT", error)

    @staticmethod
    def clear_extension(file_name):
        split_filename = file_name.split(".")
        if len(split_filename) < 2:
            return file_name

        if split_filename[-1] in ["qcow2", "vhd", "vpc", "vmdk"]:
            return '.'.join(split_filename[:-1])

    def validate_converted_image(self):
        """
        Validate the integrity of the converted image
        :raises ConversionOperationException in case validation fails
        """
        return_code, output, error = self.__exec_local_cmd("qemu-img check {file_name}".format(
            file_name=self.image_path_convert + self.converted_image_name))
        if return_code:
            raise ConversionOperationException("VALIDATE", error)

    def upload_converted_image(self):
        """
        Upload the converted image to COS bucket
        :raises ConversionOperationException in case upload fails
        """
        try:
            future = self.transfer_manager.upload(
                self.image_path_convert + self.converted_image_name, self.bucket_name, self.converted_image_name
            )
            future.result()
        except Exception as ex:
            raise ConversionOperationException("UPLOAD", ex)

    def need_resizing(self, image_name, size="100G"):
        """
        check if an image size equal to size so that no resizing is needed
        :param image_name: <string> image name to be parsed can be a vhd image or qcow2
        :param size: <string> size of the primary image IBM gen2 accepts
        :return: <boolean>
        """
        return_code, output, error = self.__exec_local_cmd(
            command="qemu-img info {image_name}".format(image_name=image_name))
        start = output.find("virtual size: ") + len("virtual size: ")
        end = output.find(" (")
        return output[start:end] != size

    @staticmethod
    def __exec_local_cmd(command):
        """
        Function to run commands on local host
        :param command: <string> command to run

        :return: <tuple> Three tuple of return code, stdout, and stderr
        """
        try:
            process = subprocess.Popen(
                command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
            )
            output, error = process.communicate()
        except FileNotFoundError as ex:
            return 1, "", ex
        else:
            return process.returncode, output, error


class VPCPlusClient:
    """
    Client to communicate with VPC+
    """
    TASK_STATUS_SUCCESSFUL = "SUCCESSFUL"
    TASK_STATUS_FAILED = "FAILED"

    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_result(self, step, status, message=None):
        """
        Send result to VPC+
        :param step: <string> one of STEPS
        :param status: <string> SUCCESSFUL/FAILED
        :param message: <string> Error message (if any)
        """
        while True:
            try:
                response = requests.patch(
                    self.webhook_url, json={"step": step, "status": status, "message": message if message else ""},
                    verify=False)
            except Exception as ex:
                print(ex)
                time.sleep(60)
                continue

            if response.status_code == 200:
                break
            elif response.status_code == 204:
                print("Task cancelled from server")
                sys.exit(1)

            time.sleep(60)
            print("Response from server: ", response.status_code)


if __name__ == "__main__":
    STEPS = ["DOWNLOAD", "CONVERT", "VALIDATE", "UPLOAD"]
    parser = argparse.ArgumentParser(description='Manage Image Conversion Tasks')
    parser.add_argument("webhook_url", help="Webhook URL to send result back to", type=str)
    args = parser.parse_args()

    vpc_plus_client = VPCPlusClient(args.webhook_url)
    current_step = STEPS[0]
    try:
        image_conversion_manager = ImageConversionManager()

        image_conversion_manager.download_image()
        vpc_plus_client.send_result(current_step, vpc_plus_client.TASK_STATUS_SUCCESSFUL)

        current_step = STEPS[1]
        image_conversion_manager.convert_image()
        vpc_plus_client.send_result(current_step, vpc_plus_client.TASK_STATUS_SUCCESSFUL)

        current_step = STEPS[2]
        image_conversion_manager.validate_converted_image()
        vpc_plus_client.send_result(current_step, vpc_plus_client.TASK_STATUS_SUCCESSFUL)

        current_step = STEPS[3]
        image_conversion_manager.upload_converted_image()
        vpc_plus_client.send_result(current_step, vpc_plus_client.TASK_STATUS_SUCCESSFUL)
    except Exception as exc:
        vpc_plus_client.send_result(current_step, vpc_plus_client.TASK_STATUS_FAILED, str(exc))
