import uuid
import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, JSON

from doosra import db


class BillingResource(db.Model):
    ID_KEY = "id"
    PERFORMED_AT_KEY = "performed_at"
    RESOURCE_TYPE_KEY = "resource_type"
    RESOURCE_DATA_KEY = "resource_data"
    ACTION_KEY = "action"

    __tablename__ = "billing_resources"

    id = Column(String(32), primary_key=True)
    performed_at = Column(DateTime, default=datetime.datetime.utcnow())

    resource_type = Column(
        String(32),
        Enum(
            "ADDRESS-PREFIX",
            "IMAGE",
            "INSTANCE",
            "INSTANCE-PROFILE",
            "LOAD-BALANCER",
            "NETWORK-ACL",
            "NETWORK-ACL-RULE",
            "PUBLIC-GATEWAY",
            "RESOURCE-GROUP",
            "SECURITY-GROUP",
            "SECURITY-GROUP-RULE",
            "SUBNET",
            "VOLUME",
            "VOLUME-ATTACHMENT",
            "VOLUME-PROFILE",
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
            "OPERATING-SYSTEM",
        ),
        nullable=False,
    )
    resource_data = Column(JSON)
    action = Column(String(32), Enum("ADD", "UPDATE", "DELETE"), nullable=True)

    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    project_id = Column(String(32), ForeignKey("projects.id"), nullable=False)
    cloud_id = Column(String(32), nullable=True)
    cloud_type = Column(String(32), Enum("AWS", "GCP", "IBM"), nullable=True)
    cloud_name = Column(String(256), nullable=True)

    def __init__(
            self,
            resource_type,
            resource_data,
            action="ADD",
            user_id=None,
            project_id=None,
            cloud_id=None,
            cloud_type=None,
            cloud_name=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.performed_at = datetime.datetime.utcnow()
        self.resource_type = resource_type
        self.resource_data = resource_data
        self.action = action
        self.user_id = user_id
        self.project_id = project_id
        self.cloud_id = cloud_id
        self.cloud_type = cloud_type
        self.cloud_name = cloud_name

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.PERFORMED_AT_KEY: self.performed_at,
            self.RESOURCE_TYPE_KEY: self.resource_type,
            self.RESOURCE_DATA_KEY: self.resource_data,
            self.ACTION_KEY: self.action,
        }
