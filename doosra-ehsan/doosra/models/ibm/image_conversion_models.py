"""
This file contains database models required for image conversion
"""
import base64
from datetime import datetime
import hashlib
import json
import os
import uuid

from Crypto.Cipher import AES
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property


from doosra import db
from doosra.common.consts import BLOCK_SIZE, DERIVATION_ROUNDS, KEY_SIZE, SALT_LENGTH, SECRET
from doosra.common.utils import decrypt_api_key


class ImageConversionInstance(db.Model):
    """
    Model containing information for VSIs in softlayer used for image conversion
    """
    __tablename__ = 'image_conversion_instances'

    STATUS_CREATE_PENDING = "CREATE_PENDING"
    STATUS_CREATING = "CREATING"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_DELETE_PENDING = "DELETE_PENDING"
    STATUS_DELETING = "DELETING"
    STATUSES = [STATUS_CREATE_PENDING, STATUS_CREATING, STATUS_ACTIVE, STATUS_DELETE_PENDING, STATUS_DELETING]

    FIXED_DOMAIN = "vpc.service.imageconversion"
    FIXED_IMAGE_GUID = "0e765b46-0fda-482b-a71a-66cb08e88358"
    FIXED_TAGS = "vpc-plus, Image Conversion, DO NOT DELETE"
    FIXED_NIC_SPEED = 1000

    id = Column(String(32), primary_key=True)
    softlayer_id = Column(Integer)
    username = Column(String(1024))
    _password = Column(String(1024))
    ip_address = Column(String(15))
    datacenter = Column(String(1024), nullable=False)
    cpus = Column(Integer, nullable=False)
    memory = Column(Integer, nullable=False)
    status = Column(Enum(STATUS_CREATE_PENDING, STATUS_CREATING, STATUS_ACTIVE, STATUS_DELETE_PENDING, STATUS_DELETING),
                    default=STATUS_CREATE_PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow(), nullable=False)

    task = relationship('ImageConversionTask', backref='instance', uselist=False)

    def __init__(self, region):
        self.id = str(uuid.uuid4().hex)
        self.datacenter = self.__get_datacenter(region)
        self.cpus = 4
        self.memory = 4

    def to_softlayer_json(self):
        """
        Function to create a json for sending to softlayer client for instance creation
        :return: <dict> dictionary containing enough information to CREATE instance on softlayer
        """
        return {
            "domain": self.FIXED_DOMAIN,
            "hostname": self.id,
            "datacenter": self.datacenter,
            "cpus": self.cpus,
            "memory": self.memory,
            "image_id": self.FIXED_IMAGE_GUID,
            "tags": self.FIXED_TAGS,
            'local_disk': True,
            "nic_speed": self.FIXED_NIC_SPEED
        }

    def update_create_time(self):
        """
        When instance becomes ACTIVE, this function can be called to update the creation time for better precision
        """
        self.created_at = datetime.utcnow()

    @staticmethod
    def __get_datacenter(region):
        """
        Function containing logic for region to datacenter translation
        :param region: <string> Region of the COS bucket to download from

        :return: <string> datacenter name in the region provided
        """
        if region == "us-south":
            return "dal13"
        elif region == "us-east":
            return "wdc07"
        elif region == "eu-gb":
            return "lon06"
        elif region == "eu-de":
            return "fra02"
        elif region == "jp-tok":
            return "tok04"

        return "dal13"

    @property
    def password(self):
        """
        Password getter to decrypt password and return it
        :return: <string> decrypted password
        """
        return self.__decrypt_password(self._password)

    @password.setter
    def password(self, new_password):
        """
        Password setter to encrypt password and set it
        :param new_password: <string> password to encrypt and store
        """
        self._password = self.__encrypt_password(new_password)

    def __encrypt_password(self, password):
        """
        Encrypt the password for instance
        :param password: <string> password to encrypt
        :return: <string> encrypted password if successful, otherwise the password string unchanged
        """
        try:
            salt = os.urandom(SALT_LENGTH)
            iv = os.urandom(BLOCK_SIZE)
            derived_secret = SECRET
            for i in range(0, DERIVATION_ROUNDS):
                derived_secret = hashlib.sha256(
                    (str(salt) + derived_secret).encode()
                ).hexdigest()

            derived_secret = derived_secret[:KEY_SIZE]
            length = 16 - (len(password) % 16)
            password += chr(length) * length
            cipher = AES.new(derived_secret, AES.MODE_CBC, iv)
            return base64.b64encode(cipher.encrypt(password) + iv + salt)
        except Exception as e:
            print("Exception encrypting password for instance {}: {}".format(self.id, e))
            return password

    def __decrypt_password(self, password):
        """
        Encrypt the password for instance
        :param password: <string> password to decrypt
        :return: <string> decrypted password if successful, otherwise the password string unchanged
        """
        try:
            secret_key = base64.b64decode(password)
            start_iv = len(secret_key) - BLOCK_SIZE - SALT_LENGTH
            start_salt = len(secret_key) - SALT_LENGTH
            data, iv, salt = (
                secret_key[:start_iv],
                secret_key[start_iv:start_salt],
                secret_key[start_salt:],
            )
            derived_secret = SECRET
            for i in range(0, DERIVATION_ROUNDS):
                derived_secret = hashlib.sha256(
                    (str(salt) + derived_secret).encode()
                ).hexdigest()

            derived_secret = derived_secret[:KEY_SIZE]
            cipher = AES.new(derived_secret, AES.MODE_CBC, iv)
            secret_key = cipher.decrypt(data)
            length = secret_key[-1]
            return secret_key[:-length].decode("utf-8")
        except Exception as e:
            print("Exception decrypting password for instance {}: {}".format(self.id, e))
            return password


class ImageConversionTask(db.Model):
    """
    Database model for Image Conversion Task having required information
    """
    __tablename__ = 'image_conversion_tasks'

    STATUS_CREATED = "CREATED"
    STATUS_RUNNING = "RUNNING"
    STATUS_SUCCESSFUL = "SUCCESSFUL"
    STATUS_FAILED = "FAILED"
    STATUSES = [STATUS_CREATED, STATUS_RUNNING, STATUS_SUCCESSFUL, STATUS_FAILED]

    STEP_PENDING_PROCESS_START = "PENDING_PROCESS_START"
    STEP_FILES_UPLOADING = "FILES_UPLOADING"
    STEP_FILES_UPLOADING_RETRY = "FILES_UPLOADING_RETRY"
    STEP_IMAGE_DOWNLOADING = "IMAGE_DOWNLOADING"
    STEP_IMAGE_DOWNLOADING_RETRY = "IMAGE_DOWNLOADING_RETRY"

    STEP_IMAGE_CONVERTING = "IMAGE_CONVERTING"

    STEP_IMAGE_VALIDATING = "IMAGE_VALIDATING"

    STEP_IMAGE_UPLOADING = "IMAGE_UPLOADING"

    STEP_PENDING_CLEANUP = "PENDING_CLEANUP"
    STEP_CLEANING_UP = "CLEANING_UP"

    STEP_PROCESS_COMPLETED = "PROCESS_COMPLETED"

    STEPS = [STEP_PENDING_PROCESS_START,
             STEP_FILES_UPLOADING,
             STEP_FILES_UPLOADING_RETRY,
             STEP_IMAGE_DOWNLOADING,
             STEP_IMAGE_DOWNLOADING_RETRY,
             STEP_IMAGE_CONVERTING,
             STEP_IMAGE_VALIDATING,
             STEP_IMAGE_UPLOADING,
             STEP_PENDING_CLEANUP,
             STEP_CLEANING_UP,
             STEP_PROCESS_COMPLETED
             ]

    # Note: This ID SHOULD NOT be provided to the frontend in any case.
    id = Column(String(32), primary_key=True)
    image_size_mb = Column(Integer, nullable=False)
    region = Column(String(16), nullable=False)
    image_name = Column(String(255), nullable=False)
    cos_bucket_name = Column(String(255), nullable=False)
    _status = Column(Enum(STATUS_CREATED, STATUS_RUNNING, STATUS_SUCCESSFUL, STATUS_FAILED), nullable=False)
    _step = Column(
        Enum(
            STEP_PENDING_PROCESS_START, STEP_FILES_UPLOADING, STEP_FILES_UPLOADING_RETRY, STEP_IMAGE_DOWNLOADING,
            STEP_IMAGE_DOWNLOADING_RETRY, STEP_IMAGE_CONVERTING, STEP_IMAGE_VALIDATING, STEP_IMAGE_UPLOADING,
            STEP_PENDING_CLEANUP, STEP_CLEANING_UP, STEP_PROCESS_COMPLETED
        ),
        nullable=False
    )
    message = Column(Text)
    retries = Column(Integer, default=20)

    created_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    download_started_at = Column(DateTime)
    conversion_started_at = Column(DateTime)
    validation_started_at = Column(DateTime)
    upload_started_at = Column(DateTime)

    instance_id = Column(String(32), ForeignKey('image_conversion_instances.id'))
    cloud_id = Column(String(32), ForeignKey('ibm_clouds.id'), nullable=False)

    def __init__(self, region, cos_bucket_name, image_name, image_size_mb):
        self.id = str(uuid.uuid4().hex)
        self.region = region
        self.cos_bucket_name = cos_bucket_name
        self.image_name = image_name
        self.image_size_mb = image_size_mb
        self.status = self.STATUS_CREATED
        self.step = self.STEP_PENDING_PROCESS_START

    def generate_config_file_contents(self):
        """
        Generate config contents as json for config.json for remote host
        :return: <string> config.json contents for conversion script as string
        """
        return json.dumps({
            "IMAGE_FILE_NAME": self.image_name,
            "DESTINATION_IMAGE_FORMAT": "qcow2",
            "IBM_API_KEY_ID": decrypt_api_key(self.ibm_cloud.api_key),
            "IAM_SERVICE_ID": self.ibm_cloud.service_credentials.resource_instance_id,
            "S3_ENDPOINT": "https://s3.direct.{region}.cloud-object-storage.appdomain.cloud".format(
                region=self.region),
            "BUCKET_NAME": self.cos_bucket_name,
            "DOWNLOAD_PATH": "/mnt/image_conversion/",
            "CONVERT_PATH": "/mnt/image_conversion/"
        })

    @property
    def webhook_url(self):
        """
        Property for task webhook URL for steps and status updates
        :return: <string> webhook URL e.g http://localhost:80/v1/ibm/image_conversion/<task_id>
        """
        return os.environ.get("WEBHOOK_BASE_URL") + self.id

    @hybrid_property
    def status(self):
        """
        Getter for the column value of _status
        :return: <string> column value of _status
        """
        return self._status

    @status.setter
    def status(self, new_status):
        """
        Setter for the column value of _status
        :param new_status: <string> new status value
        """
        assert new_status in self.STATUSES

        if new_status == self.STATUS_CREATED:
            self.created_at = datetime.utcnow()
        elif new_status == self.STATUS_RUNNING:
            self.started_at = datetime.utcnow()
        elif new_status == self.STATUS_FAILED:
            self.completed_at = datetime.utcnow()
        elif new_status == self.STATUS_SUCCESSFUL:
            self.completed_at = datetime.utcnow()
            db.session.add(ImageConversionTaskLog(self))

        self._status = new_status

    @hybrid_property
    def step(self):
        """
        Getter for the column value of _step
        :return: <string> column value of _step
        """
        return self._step

    @step.setter
    def step(self, new_step):
        """
        Setter for the column value of _step
        :param new_step: <string> new status value
        """
        assert new_step in self.STEPS

        if new_step == self.STEP_IMAGE_DOWNLOADING:
            self.download_started_at = datetime.utcnow()
        elif new_step == self.STEP_IMAGE_CONVERTING:
            self.conversion_started_at = datetime.utcnow()
        elif new_step == self.STEP_IMAGE_VALIDATING:
            self.validation_started_at = datetime.utcnow()
        elif new_step == self.STEP_IMAGE_UPLOADING:
            self.upload_started_at = datetime.utcnow()

        self._step = new_step


class ImageConversionTaskLog(db.Model):
    """
    Database model for SUCCESSFUL Image Conversion Tasks info storage
    """
    __tablename__ = 'image_conversion_task_logs'

    id = Column(String(32), primary_key=True)
    image_size = Column(Integer, nullable=False)
    download_time = Column(Integer, nullable=False)
    convert_time = Column(Integer, nullable=False)
    upload_time = Column(Integer, nullable=False)
    completion_time = Column(Integer, nullable=False)

    def __init__(self, task):
        self.id = str(uuid.uuid4().hex)
        self.image_size = task.image_size_mb
        self.download_time = (task.conversion_started_at - task.download_started_at).seconds
        self.convert_time = (task.validation_started_at - task.conversion_started_at).seconds
        self.upload_time = (task.completed_at - task.upload_started_at).seconds
        self.completion_time = (task.completed_at - task.created_at).seconds
