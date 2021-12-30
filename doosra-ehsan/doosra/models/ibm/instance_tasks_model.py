import uuid

from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Enum,
    Boolean,
    Integer,
    JSON,
    Text
)

from doosra import db
from doosra.common.consts import IN_PROGRESS, FAILED, SUCCESS


class IBMInstanceTasks(db.Model):
    ID_KEY = "id"
    STATUS_KEY = "status"
    TYPE_KEY = "type"
    IMAGE_LOCATION_KEY = "image_location"
    BUCKET_NAME_KEY = "bucket_name"
    BUCKET_OBJECT_KEY = "bucket_object"
    VPC_IMAGE_NAME_KEY = "vpc_image"
    CLASSICAL_ACCOUNT_ID_KEY = "classical_account_id"
    CLASSICAL_INSTANCE_ID_KEY = "classical_instance_id"
    CLASSICAL_IMAGE_ID_KEY = "classical_image_id"
    IMAGE_TYPE_KEY = "image_type"
    IN_FOCUS_KEY = "in_focus"

    TYPE_TAKE_SNAPSHOT = "take_snapshot"
    TYPE_UPLOAD_TO_COS = "upload_to_cos"
    TYPE_IMAGE_CONVERSION = "image_conversion"
    TYPE_CREATE_CUSTOM_IMAGE = "create_custom_image"
    TYPE_CREATE_VSI = "create_instance_subsequent"

    LOCATION_CLASSICAL_VSI = "classical_vsi"
    LOCATION_CLASSICAL_IMAGE = "classical_image"
    LOCATION_COS_VHD = "cos_vhd"
    LOCATION_COS_VMDK = "cos_vmdk"
    LOCATION_COS_QCOW2 = "cos_qcow2"
    LOCATION_CUSTOM_IMAGE = "custom_image"
    LOCATION_PUBLIC_IMAGE = "public_image"
    BACKUP_REQ_JSON_KEY = "backup_req_json"

    __tablename__ = "ibm_instances_tasks"

    id = Column(String(32), primary_key=True)
    base_task_id = Column(String(32), nullable=False)
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    instance_id = Column(String(32), ForeignKey("ibm_instances.id"), nullable=True)

    status = Column(Enum(IN_PROGRESS, FAILED, SUCCESS), nullable=False)
    task_type = Column(
        Enum(TYPE_TAKE_SNAPSHOT, TYPE_UPLOAD_TO_COS, TYPE_IMAGE_CONVERSION, TYPE_CREATE_CUSTOM_IMAGE,
             TYPE_CREATE_VSI),
        nullable=False)
    image_location = Column(
        Enum(LOCATION_CLASSICAL_VSI, LOCATION_CLASSICAL_IMAGE, LOCATION_COS_VHD, LOCATION_COS_VMDK, LOCATION_COS_QCOW2,
             LOCATION_CUSTOM_IMAGE, LOCATION_PUBLIC_IMAGE), nullable=False)
    classical_account_id = Column(String(32), nullable=True)
    classical_instance_id = Column(Integer, nullable=True)
    classical_image_id = Column(String(32), nullable=True)
    classical_image_name = Column(String(255), nullable=True)
    bucket_name = Column(String(255), nullable=True)
    bucket_object = Column(String(255), nullable=True)
    vpc_image_name = Column(String(255), nullable=True)
    custom_image = Column(String(255), nullable=True)
    public_image = Column(String(255), nullable=True)
    in_focus = Column(Boolean, nullable=False, default=False)
    image_conversion_task_id = Column(String(32), nullable=True)
    image_type = Column(Integer, nullable=True)
    image_create_date = Column(String(32), nullable=True)
    backup_req_json = Column(JSON, default={})
    fe_json = Column(JSON, default={})

    def __init__(
            self, base_task_id, cloud_id, instance_id, status, task_type, image_location, classical_account_id=None,
            classical_instance_id=None, classical_image_id=None, classical_image_name=None, bucket_name=None,
            bucket_object=None, vpc_image_name=None, custom_image=None, public_image=None, in_focus=False,
            image_conversion_task_id=None, image_create_date=None, image_type=None, backup_req_json=None, fe_json=None):
        self.id = str(uuid.uuid4().hex)
        self.base_task_id = base_task_id
        self.cloud_id = cloud_id
        self.instance_id = instance_id
        self.status = status
        self.task_type = task_type
        self.image_location = image_location
        self.classical_account_id = classical_account_id
        self.classical_instance_id = classical_instance_id
        self.classical_image_id = classical_image_id
        self.classical_image_name = classical_image_name
        self.bucket_name = bucket_name
        self.bucket_object = bucket_object
        self.vpc_image_name = vpc_image_name
        self.custom_image = custom_image
        self.public_image = public_image
        self.in_focus = in_focus
        self.image_conversion_task_id = image_conversion_task_id
        self.image_create_date = image_create_date
        self.image_type = image_type
        self.backup_req_json = backup_req_json
        self.fe_json = fe_json

    def to_json(self):
        return {
            self.IMAGE_LOCATION_KEY: self.image_location,
            self.VPC_IMAGE_NAME_KEY: self.vpc_image_name,
            self.CLASSICAL_ACCOUNT_ID_KEY: self.classical_account_id,
            self.CLASSICAL_INSTANCE_ID_KEY: self.classical_instance_id,
            self.CLASSICAL_IMAGE_ID_KEY: self.classical_image_id,
            self.BUCKET_NAME_KEY: self.bucket_name,
            self.BUCKET_OBJECT_KEY: self.bucket_object,
            self.LOCATION_PUBLIC_IMAGE: self.public_image,
            self.LOCATION_CUSTOM_IMAGE: self.custom_image,
            self.IMAGE_TYPE_KEY: self.image_type,
            self.IN_FOCUS_KEY: self.in_focus,
            "migration": self.image_location == IBMInstanceTasks.LOCATION_CLASSICAL_VSI
        }
