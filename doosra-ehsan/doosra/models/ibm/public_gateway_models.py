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
from doosra.common.consts import (
    CREATION_PENDING,
    CREATED,
    ERROR_CREATING, PENDING,
)


class IBMPublicGateway(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    REGION_KEY = "region"
    ZONE_KEY = "zone"
    SUBNETS_KEY = "subnets"
    VPC_KEY = "vpc"
    FLOATING_IP_KEY = "floating_ip"
    CLOUD_ID_KEY = "cloud_id"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_public_gateways"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    region = Column(String(255), nullable=True)
    zone = Column(String(255), nullable=False)

    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    subnets = relationship("IBMSubnet", backref="ibm_public_gateway", lazy="dynamic")
    floating_ip = relationship(
        "IBMFloatingIP", backref="ibm_public_gateway", uselist=False
    )

    __table_args__ = (
        UniqueConstraint(
            name, vpc_id, cloud_id, region,
            name="uix_ibm_public_gateway_name_vpc_cloud_id"
        ),
    )

    def __init__(self, name, region, zone, resource_id=None, status=CREATION_PENDING, cloud_id=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.zone = zone
        self.resource_id = resource_id
        self.status = status
        self.cloud_id = cloud_id

    def set_error_status(self):
        if not self.status == CREATED:
            self.status = ERROR_CREATING
        db.session.commit()

    def make_copy(self):
        obj = IBMPublicGateway(
            self.name, self.region, self.zone, self.resource_id, self.status, self.cloud_id
        )
        if self.floating_ip:
            obj.floating_ip = self.floating_ip.make_copy()

        if self.resource_group_id:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()
        return obj

    def get_existing_from_db(self, vpc=None):
        if vpc:
            return (
                db.session.query(self.__class__)
                .filter_by(name=self.name, region=self.region, cloud_id=self.cloud_id, vpc_id=vpc.id)
                .first()
            )
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, region=self.region, cloud_id=self.cloud_id, vpc_id=self.vpc_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.zone == other.zone)
            and (self.region == other.region)
            and (self.resource_id == other.resource_id)
            and (self.status == other.status)
        ):
            return False

        if (self.floating_ip and not other.floating_ip) or (
            not self.floating_ip and other.floating_ip
        ):
            return False

        if self.floating_ip and other.floating_ip:
            if not self.floating_ip.params_eq(other.floating_ip):
                return False

        return True

    def add_update_db(self, vpc=None):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            floating_ip = self.floating_ip
            self.floating_ip = None
            self.subnets = list()
            self.ibm_vpc_network = vpc
            db.session.add(self)
            db.session.commit()

            if floating_ip:
                self.floating_ip = floating_ip.add_update_db()
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.region = self.region
            existing.zone = self.zone
            existing.resource_id = self.resource_id
            db.session.commit()

            floating_ip = self.floating_ip
            self.floating_ip = None

            if floating_ip:
                existing.floating_ip = floating_ip.add_update_db()
            else:
                existing.floating_ip = None
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.REGION_KEY: self.region,
            self.ZONE_KEY: self.zone,
            self.STATUS_KEY: self.status,
            self.VPC_KEY: {
                self.ID_KEY: self.ibm_vpc_network.id,
                self.NAME_KEY: self.ibm_vpc_network.name,
            }
            if self.ibm_vpc_network
            else None,
            self.FLOATING_IP_KEY: self.floating_ip.to_json()
            if self.floating_ip
            else None,
            self.SUBNETS_KEY: [subnet.to_json() for subnet in self.subnets.all()],
            self.CLOUD_ID_KEY: self.cloud_id,
        }

    def to_json_body(self):
        obj = {
            "name": self.name,
            "zone": {"name": self.zone},
            "vpc": {
                "id": self.ibm_vpc_network.resource_id if self.ibm_vpc_network else None
            },
        }
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
        # TODO: store ibm status as well and make this status a hybrid property

        status = None
        if json_body["status"] == "pending":
            status = "CREATING"
        elif json_body["status"] == "available":
            status = "CREATED"
        elif json_body["status"] == "deleting":
            status = "DELETING"
        elif json_body["status"] == "failed":
            status = "ERROR_"

        assert status
        ibm_public_gateway = IBMPublicGateway(
            name=json_body["name"], region=region, zone=json_body["zone"]["name"], resource_id=json_body["id"],
            status=status
        )

        return ibm_public_gateway
