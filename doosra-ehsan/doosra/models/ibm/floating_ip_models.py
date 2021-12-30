import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
)
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import CREATION_PENDING, PENDING


class IBMFloatingIP(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    ZONE_KEY = "zone"
    REGION_KEY = "region"
    STATUS_KEY = "status"
    ADDRESS_KEY = "address"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_floating_ips"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    region = Column(String(255), nullable=False)
    zone = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    address = Column(String(255))

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    public_gateway_id = Column(String(32), ForeignKey("ibm_public_gateways.id"))
    network_interface_id = Column(String(32), ForeignKey("ibm_network_interfaces.id"))
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    __table_args__ = (
        UniqueConstraint(
            name, region, cloud_id, name="uix_ibm_floating_ip_name_region_cloud_id"
        ),
    )

    def __init__(
        self,
        name,
        region,
        zone,
        address=None,
        resource_id=None,
        status=None,
        cloud_id=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.status = status or CREATION_PENDING
        self.zone = zone
        self.address = address
        self.resource_id = resource_id
        self.cloud_id = cloud_id

    def make_copy(self):
        obj = IBMFloatingIP(
            name=self.name,
            region=self.region,
            zone=self.zone,
            address=self.address,
            resource_id=self.resource_id,
            status=self.status,
            cloud_id=self.cloud_id,
        )
        if self.resource_group_id:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()
        return obj

    def get_existing_from_db(self):
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, cloud_id=self.cloud_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.zone == other.zone)
            and (self.address == other.address)
            and (self.resource_id == other.resource_id)
            and (self.status == other.status)
            and (self.region == other.region)
        ):
            return False

        return True

    def add_update_db(self):
        existing = self.get_existing_from_db()
        if not existing:
            db.session.add(self)
            db.session.commit()
            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.zone = self.zone
            existing.region = self.region
            existing.status = self.status
            existing.address = self.address
            existing.resource_id = self.resource_id
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.REGION_KEY: self.region,
            self.ZONE_KEY: self.zone,
            self.STATUS_KEY: self.status,
            self.ADDRESS_KEY: self.address,
        }

    def to_json_body(self):
        json_data = {"name": self.name}

        if self.resource_group_id:
            json_data["resource_group"] = {"id": self.ibm_resource_group.resource_id}

        if self.ibm_public_gateway:
            json_data["target"] = {self.ID_KEY: self.ibm_public_gateway.resource_id}
        elif self.ibm_network_interface:
            json_data["target"] = {self.ID_KEY: self.ibm_network_interface.resource_id}
        else:
            json_data["zone"] = {"name": self.zone}

        return json_data

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }

    @classmethod
    def from_ibm_json_body(cls, region, json_body):
        """
        This method is for the purpose of creating a model object out of a JSON. This JSON can be from ibm cloud
        """
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
        # TODO: Verify Schema
        return IBMFloatingIP(
            name=json_body["name"],
            region=region,
            zone=json_body["zone"]["name"],
            address=json_body["address"],
            resource_id=json_body["id"],
            status=status,
        )
