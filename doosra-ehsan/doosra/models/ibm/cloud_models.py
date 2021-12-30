import uuid
from datetime import datetime
from datetime import timedelta

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    JSON
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import relationship

from doosra import db
from doosra.common.consts import (
    CREATED,
    SUCCESS,
    FAILED, DELETING,
)
from doosra.common.utils import encrypt_api_key, decrypt_api_key
from doosra.models.common_models import JSONEncodedDict, MutableDict


class IBMCloud(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    VPC_NETWORK_KEY = "vpc_networks"
    RESOURCE_GROUP_KEY = "resource_groups"
    NETWORK_ACL_KEY = "network_acls"
    SECURITY_GROUP_KEY = "security_groups"
    PUBLIC_GATEWAY_KEY = "public_gateways"
    VPNS_KEY = "vpn_gateways"
    LOAD_BALANCERS_KEY = "load_balancers"
    IKE_POLICY_KEY = "ike_policies"
    IPSEC_POLICY_KEY = "ipsec_policies"
    INSTANCES_KEY = "instances"
    SSH_KEY = "ssh_keys"
    IMAGES_KEY = "images"
    SERVICE_CREDENTIALS_KEY = "service_credentials"

    STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS = "ERROR_DUPLICATE_RESOURCE_GROUPS"

    __tablename__ = "ibm_clouds"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    api_key = Column(String(500), nullable=False)
    status = Column(Enum("AUTHENTICATING", "INVALID", "VALID", DELETING, STATUS_ERROR_DUPLICATE_RESOURCE_GROUPS),
                    nullable=False)

    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)

    group_id = Column(String(32), default=None)

    service_credentials = relationship(
        "IBMServiceCredentials",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        uselist=False
    )

    dedicated_hosts = relationship("IBMDedicatedHost", backref="ibm_cloud", cascade="all, delete-orphan",
                                   lazy="dynamic")
    dedicated_host_groups = relationship("IBMDedicatedHostGroup", backref="ibm_cloud", cascade="all, delete-orphan",
                                         lazy="dynamic")
    dedicated_host_profiles = relationship("IBMDedicatedHostProfile", backref="ibm_cloud", cascade="all, delete-orphan",
                                           lazy="dynamic")
    kubernetes_clusters = relationship(
        "KubernetesCluster",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    ike_policies = relationship(
        "IBMIKEPolicy",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    ipsec_policies = relationship(
        "IBMIPSecPolicy",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    credentials = relationship(
        "IBMCredentials",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        uselist=False,
    )
    ibm_tasks = relationship(
        "IBMTask", backref="ibm_cloud", cascade="all, delete-orphan", lazy="dynamic"
    )
    resource_groups = relationship(
        "IBMResourceGroup",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    vpc_networks = relationship(
        "IBMVpcNetwork",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    vpc_routes = relationship(
        "IBMVpcRoute", backref="ibm_cloud", cascade="all, delete-orphan", lazy="dynamic"
    )
    load_balancers = relationship(
        "IBMLoadBalancer",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    network_acls = relationship(
        "IBMNetworkAcl",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    public_gateways = relationship(
        "IBMPublicGateway",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    security_groups = relationship(
        "IBMSecurityGroup",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    floating_ips = relationship(
        "IBMFloatingIP",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    instances = relationship(
        "IBMInstance", backref="ibm_cloud", cascade="all, delete-orphan", lazy="dynamic"
    )
    ssh_keys = relationship(
        "IBMSshKey", backref="ibm_cloud", cascade="all, delete-orphan", lazy="dynamic"
    )
    instance_profiles = relationship(
        "IBMInstanceProfile",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    images = relationship(
        "IBMImage", backref="ibm_cloud", cascade="all, delete-orphan", lazy="dynamic"
    )
    volumes = relationship(
        "IBMVolume", backref="ibm_cloud", cascade="all, delete-orphan", lazy="dynamic"
    )
    volume_profiles = relationship(
        "IBMVolumeProfile",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    vpn_gateways = relationship(
        "IBMVpnGateway",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    operating_systems = relationship(
        "IBMOperatingSystem",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    subnets = relationship(
        "IBMSubnet",
        backref="ibm_cloud",
        cascade="all,delete-orphan",
        lazy="dynamic"
    )
    image_conversion_tasks = relationship(
        "ImageConversionTask",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    transit_gateways = relationship(
        "TransitGateway",
        backref="ibm_cloud",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __init__(self, name, api_key, project_id):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.api_key = encrypt_api_key(api_key)
        self.status = "AUTHENTICATING"
        self.project_id = project_id

    def verify_api_key(self, api_key):
        return api_key == decrypt_api_key(self.api_key)

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.SERVICE_CREDENTIALS_KEY: True if self.service_credentials else False
        }

    def to_json_body(self):
        return {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": decrypt_api_key(self.api_key),
        }

    def update_from_auth_response(self, auth_response):
        self.credentials.access_token = " ".join([auth_response.get("token_type"), auth_response.get("access_token")])
        self.credentials.expiration_date = datetime.utcnow() + timedelta(seconds=auth_response.get("expires_in"))

    @property
    def auth_required(self):
        if not (self.credentials.access_token and self.credentials.expiration_date):
            return True
        if (self.credentials.expiration_date - datetime.utcnow()).total_seconds() < 120:
            return True
        return False

    def update_token(self, credentials):
        self.credentials.access_token = credentials.access_token
        self.credentials.expiration_date = credentials.expiration_date
        db.session.commit()


class IBMServiceCredentials(db.Model):
    __tablename__ = "ibm_service_credentials"

    RESOURCE_INSTANCE_ID_KEY = "resource_instance_id"

    id = Column(String(32), primary_key=True)
    resource_instance_id = Column(String(1000), nullable=False)
    access_key_id = Column(String(500), nullable=True)
    secret_access_key = Column(String(500), nullable=True)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)

    def __init__(self, resource_instance_id, access_key_id=None, secret_access_key=None):
        self.id = str(uuid.uuid4().hex)
        self.resource_instance_id = resource_instance_id
        self.access_key_id = encrypt_api_key(access_key_id) if access_key_id else None
        self.secret_access_key = encrypt_api_key(secret_access_key) if secret_access_key else None


class IBMCredentials(db.Model):
    ID_KEY = "id"
    ACCESS_TOKEN_KEY = "access_token"
    REFRESH_TOKEN_KEY = "refresh_token"
    EXPIRATION_DATE_KEY = "expiration_date"

    __tablename__ = "ibm_credentials"

    id = Column(String(32), primary_key=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    expiration_date = Column(DateTime)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)

    def __init__(self, credentials):
        self.id = str(uuid.uuid4().hex)
        self.access_token = " ".join(
            [credentials.get("token_type"), credentials.get("access_token")]
        )
        self.refresh_token = credentials.get("refresh_token")
        self.expiration_date = datetime.now() + timedelta(
            seconds=credentials.get("expires_in")
        )

    def update_token(self, credentials):
        self.access_token = credentials.access_token
        self.expiration_date = credentials.expiration_date
        db.session.commit()

    def is_token_expired(self):
        if (self.expiration_date - datetime.now()).total_seconds() < 120:
            return True

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.ACCESS_TOKEN_KEY: self.access_token,
            self.REFRESH_TOKEN_KEY: self.refresh_token,
            self.EXPIRATION_DATE_KEY: self.expiration_date,
        }


class IBMTask(db.Model):
    ID_KEY = "id"
    CLOUD_ID_KEY = "cloud_id"
    STATUS_KEY = "status"
    ACTION_KEY = "action"
    TYPE_KEY = "type"
    RESOURCE_ID_KEY = "resource_id"
    RESULT_KEY = "result"
    STARTED_AT_KEY = "started_at"
    REGION_KEY = "region"
    MESSAGE_KEY = "message"
    TRACE_ID_KEY = "trace_id"
    REPORT = "report"

    __tablename__ = "ibm_tasks"

    id = Column(String(100), primary_key=True)

    type = Column(
        String(32),
        Enum(
            "ADDRESS-PREFIX",
            "DEDICATED-HOST",
            "DEDICATED-HOST-GROUP",
            "DEDICATED-HOST-PROFILE"
            "IMAGE",
            "INSTANCE",
            "INSTANCE-PROFILE",
            "LOAD-BALANCER",
            "NETWORK-ACL",
            "NETWORK-ACL-RULE",
            "PUBLIC-GATEWAY",
            "REGION",
            "RESOURCE-GROUP",
            "SECURITY-GROUP",
            "SECURITY-GROUP-RULE",
            "SUBNET",
            "VOLUME-PROFILE",
            "ZONE",
            "VPC-ROUTE",
            "VPC",
            "SSH-KEY",
            "VPN-GATEWAY",
            "TRANSIT-GATEWAY",
            "TRANSIT-GATEWAY-CONNECTION",
            "TRANSIT-LOCATION",
            "VPN-CONNECTION",
            "IKE-POLICY",
            "FLOATING-IP",
            "IPSEC-POLICY",
            "BUCKET",
            "BUCKET-OBJECT"
            "OPERATING-SYSTEM",
            "K8S_CLUSTER"
        ),
        nullable=False,
    )

    _status = Column(String(32), Enum(CREATED, SUCCESS, FAILED), nullable=False)
    action = Column(String(32), Enum("ADD", "UPDATE", "DELETE", "SYNC"), nullable=False)
    region = Column(String(32), nullable=True)
    result = Column(MutableDict.as_mutable(JSONEncodedDict), nullable=True)
    resource_id = Column(String(64), nullable=True)
    message = Column(String(500), nullable=True)
    started_at = Column(DateTime, nullable=False)
    last_updated_at = Column(DateTime, onupdate=datetime.utcnow())
    completed_at = Column(DateTime)
    trace_id = Column(String(100))
    request_payload = Column(MEDIUMTEXT)
    report = Column(JSON)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"))

    def __init__(
            self, task_id, type_, action, cloud_id, resource_id=None, message=None, region=None, trace_id=None,
            request_payload=None
    ):
        self.id = task_id or str(uuid.uuid4().hex)
        self.status = CREATED
        self.started_at = datetime.utcnow()
        self.type = type_
        self.action = action
        self.resource_id = resource_id
        self.message = message
        self.region = region
        self.trace_id = trace_id
        self.cloud_id = cloud_id
        self.request_payload = request_payload

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        if value == SUCCESS or value == FAILED:
            self.completed_at = datetime.utcnow()

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.STATUS_KEY: self.status,
            self.ACTION_KEY: self.action,
            self.TYPE_KEY: self.type,
            self.REGION_KEY: self.region,
            self.RESULT_KEY: self.result,
            self.RESOURCE_ID_KEY: self.resource_id,
            self.MESSAGE_KEY: self.message,
            self.CLOUD_ID_KEY: self.cloud_id,
            self.STARTED_AT_KEY: str(self.started_at),
            self.TRACE_ID_KEY: self.trace_id,
            self.REPORT: self.report
        }


class IBMSubTask(db.Model):
    ID_KEY = "id"
    RESOURCE_ID_KEY = "resource_id"

    __tablename__ = "ibm_sub_tasks"

    id = Column(String(100), primary_key=True)
    resource_id = Column(String(64), nullable=True)
    status = Column(String(32), Enum(CREATED, SUCCESS, FAILED), nullable=False)

    def __init__(self, task_id, resource_id, status=CREATED):
        self.id = task_id
        self.resource_id = resource_id
        self.status = status
