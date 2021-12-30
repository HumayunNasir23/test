import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    String,
)
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import (
    CREATION_PENDING,
    CREATED,
    ERROR_CREATING, PENDING,
)


class IBMSshKey(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    TYPE_KEY = "type"
    PUBLIC_KEY = "public_key"
    FINGER_PRINT_KEY = "finger_print"
    REGION_KEY = "region"
    STATUS_KEY = "status"
    CLOUD_ID_KEY = "cloud_id"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_ssh_keys"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    region = Column(String(255), nullable=False)
    resource_id = Column(String(64))
    status = Column(String(50), nullable=False)
    type = Column(Enum("rsa"), default="rsa", nullable=False)
    public_key = Column(String(1024))
    finger_print = Column(String(512))

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    __table_args__ = (
        UniqueConstraint(name, region, cloud_id,
                         name="uix_ibm_ssh_name_region_cloud_id"),
    )

    def __init__(
        self,
        name,
        type_,
        public_key,
        region,
        finger_print=None,
        status=None,
        resource_id=None,
        cloud_id=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = status or CREATION_PENDING
        self.resource_id = resource_id
        self.region = region
        self.finger_print = finger_print
        self.type = type_ or "rsa"
        self.public_key = public_key
        self.cloud_id = cloud_id

    def set_error_status(self):
        if not self.status == CREATED:
            self.status = ERROR_CREATING
            db.session.commit()

    def make_copy(self):
        obj = IBMSshKey(
            name=self.name,
            type_=self.type,
            public_key=self.public_key,
            region=self.region,
            finger_print=self.finger_print,
            status=self.status,
            resource_id=self.resource_id,
            cloud_id=self.cloud_id,
        )

        if self.ibm_resource_group:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()

        return obj

    def get_existing_from_db(self):
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, cloud_id=self.cloud_id, region=self.region)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.region == other.region)
            and (self.type == other.type)
            and (self.public_key == other.public_key)
            and (self.resource_id == other.resource_id)
            and (self.status == other.status)
        ):
            return False

        return True

    def add_update_db(self):
        existing = self.get_existing_from_db()
        if not existing:
            ibm_resource_group = self.ibm_resource_group
            self.ibm_resource_group = None
            db.session.add(self)
            db.session.commit()

            if ibm_resource_group:
                self.ibm_resource_group = ibm_resource_group.add_update_db()
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.resource_id = self.resource_id
            existing.region = self.region
            existing.type = self.type
            existing.public_key = self.public_key
            db.session.commit()

            ibm_resource_group = self.ibm_resource_group
            self.ibm_resource_group = None

            if ibm_resource_group:
                existing.ibm_resource_group = ibm_resource_group.add_update_db()
            else:
                existing.ibm_resource_group = None
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.TYPE_KEY: self.type,
            self.PUBLIC_KEY: self.public_key,
            self.FINGER_PRINT_KEY: self.finger_print,
            self.REGION_KEY: self.region,
            self.STATUS_KEY: self.status,
            self.CLOUD_ID_KEY: self.cloud_id,
        }

    def to_json_body(self):
        obj = {"name": self.name, "public_key": self.public_key, "type": self.type}
        if self.ibm_resource_group:
            obj["resource_group"] = {"id": self.ibm_resource_group.resource_id}
        return obj

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }

    @classmethod
    def from_ibm_json_body(cls, region, json_body):
        ibm_ssh_key = IBMSshKey(
            name=json_body["name"],
            type_=json_body["type"],
            public_key=json_body["public_key"],
            region=region,
            finger_print=json_body["fingerprint"],
            status="CREATED",
            resource_id=json_body["id"],
        )

        return ibm_ssh_key
