import uuid

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import CREATION_PENDING, PENDING


class IBMAddressPrefix(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    ADDRESS_KEY = "address"
    STATUS_KEY = "status"
    ZONE_KEY = "zone"
    IS_DEFAULT_KEY = "is_default"
    CLOUD_ID_KEY = "cloud_id"
    VPC_ID_KEY = "vpc_id"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_address_prefixes"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    address = Column(String(255))
    status = Column(String(50), nullable=False)
    zone = Column(String(50), nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)

    subnets = relationship(
        "IBMSubnet",
        backref="ibm_address_prefix",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(name, vpc_id, name="uix_ibm_address_prefix_name_vpc_id"),
    )

    def __init__(
        self,
        name,
        zone,
        vpc_id=None,
        address=None,
        resource_id=None,
        status=CREATION_PENDING,
        is_default=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.zone = zone
        self.address = address
        self.status = status
        self.is_default = is_default
        self.resource_id = resource_id

        if vpc_id:
            self.vpc_id = vpc_id

    def make_copy(self):
        return IBMAddressPrefix(
            name=self.name,
            zone=self.zone,
            address=self.address,
            resource_id=self.resource_id,
            status=self.status,
            is_default=self.is_default,
        )

    def get_existing_from_db(self, vpc=None):
        if vpc:
            return (
                db.session.query(self.__class__)
                .filter_by(name=self.name, vpc_id=vpc.id)
                .first()
            )

        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, vpc_id=self.vpc_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.zone == other.zone)
            and (self.resource_id == other.resource_id)
            and (self.address == other.address)
            and (self.is_default == other.is_default)
            and (self.status == other.status)
        ):
            return False
        return True

    def add_update_db(self, vpc):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            self.ibm_vpc_network = vpc
            self.subnets = list()
            db.session.add(self)
            db.session.commit()
            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.zone = self.zone
            existing.address = self.address
            existing.is_default = self.is_default
            existing.resource_id = self.resource_id
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.ZONE_KEY: self.zone,
            self.STATUS_KEY: self.status,
            self.ADDRESS_KEY: self.address,
            self.IS_DEFAULT_KEY: self.is_default,
            self.CLOUD_ID_KEY: self.ibm_vpc_network.cloud_id if self.ibm_vpc_network else None,
            self.VPC_ID_KEY: self.vpc_id,
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "is_default": self.is_default,
            "cidr": self.address,
            "zone": {"name": self.zone},
        }

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        ibm_address_prefix = IBMAddressPrefix(
            name=json_body["name"], zone=json_body["zone"]["name"], address=json_body["cidr"],
            resource_id=json_body["id"], is_default=json_body["is_default"]
        )

        return ibm_address_prefix
