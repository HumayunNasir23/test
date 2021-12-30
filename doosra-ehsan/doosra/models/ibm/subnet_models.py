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


class IBMSubnet(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    REGION_KEY = "region"
    ZONE_KEY = "zone"
    STATUS_KEY = "status"
    IP_CIDR_BLOCK = "ip_cidr_block"
    ACL_KEY = "attached_acl"
    VPC_KEY = "vpc"
    PUBLIC_GATEWAY = "public_gateway"
    ADDRESS_PREFIX_KEY = "address_prefix"
    CLOUD_ID_KEY = "cloud_id"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_subnets"

    id = Column(String(32), primary_key=True)
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"))
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    region = Column(String(255), nullable=True)
    zone = Column(String(255), nullable=False)
    ipv4_cidr_block = Column(String(255), nullable=False)

    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)
    network_acl_id = Column(String(32), ForeignKey("ibm_network_acls.id"))
    public_gateway_id = Column(String(32), ForeignKey("ibm_public_gateways.id"))
    address_prefix_id = Column(String(32), ForeignKey("ibm_address_prefixes.id"))
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    network_interfaces = relationship(
        "IBMNetworkInterface",
        backref="ibm_subnet",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    vpn_gateways = relationship("IBMVpnGateway", backref="ibm_subnet", lazy="dynamic")

    __table_args__ = (
        UniqueConstraint(name, cloud_id, vpc_id, region, name="uix_ibm_subnet_name_cloud_id_vpc_id"),
    )

    def __init__(
        self,
        name,
        zone,
        ipv4_cidr_block,
        region,
        vpc_id=None,
        resource_id=None,
        status=CREATION_PENDING,
        cloud_id=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = status
        self.ipv4_cidr_block = ipv4_cidr_block
        self.zone = zone
        self.region = region
        self.resource_id = resource_id
        self.vpc_id = vpc_id
        self.cloud_id = cloud_id

    def set_error_status(self):
        if not self.status == CREATED:
            self.status = ERROR_CREATING

        db.session.commit()

    def make_copy(self):
        obj = IBMSubnet(
            name=self.name,
            zone=self.zone,
            ipv4_cidr_block=self.ipv4_cidr_block,
            resource_id=self.resource_id,
            status=self.status,
            cloud_id=self.cloud_id,
            region=self.region,
        )
        if self.network_acl:
            obj.network_acl = self.network_acl.make_copy()

        if self.ibm_public_gateway:
            obj.ibm_public_gateway = self.ibm_public_gateway.make_copy()

        if self.ibm_address_prefix:
            obj.ibm_address_prefix = self.ibm_address_prefix.make_copy()

        if self.resource_group_id:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()

        return obj

    def get_existing_from_db(self, vpc=None):
        if vpc:
            return (
                db.session.query(self.__class__)
                .filter_by(name=self.name, region=self.region, vpc_id=vpc.id)
                .first()
            )
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, region=self.region, vpc_id=self.vpc_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.zone == other.zone)
            and (self.region == other.region)
            and (self.status == other.status)
            and (self.resource_id == other.resource_id)
            and (self.ipv4_cidr_block == other.ipv4_cidr_block)
        ):
            return False

        if (self.network_acl and not other.network_acl) or (
            not self.network_acl and other.network_acl
        ):
            return False

        if self.network_acl and other.network_acl:
            if not self.network_acl.params_eq(other.network_acl):
                return False

        if (self.ibm_public_gateway and not other.ibm_public_gateway) or (
            not self.ibm_public_gateway and other.ibm_public_gateway
        ):
            return False

        if self.ibm_public_gateway and other.ibm_public_gateway:
            if not self.ibm_public_gateway.params_eq(other.ibm_public_gateway):
                return False

        if (self.ibm_address_prefix and not other.ibm_address_prefix) or (
            not self.ibm_address_prefix and other.ibm_address_prefix
        ):
            return False

        if self.ibm_address_prefix and other.ibm_address_prefix:
            if not self.ibm_address_prefix.params_eq(other.ibm_address_prefix):
                return False

        return True

    def add_update_db(self, vpc):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            public_gateway, network_acl, address_prefix = (
                self.ibm_public_gateway,
                self.network_acl,
                self.ibm_address_prefix,
            )
            self.network_acl, self.ibm_public_gateway, self.ibm_address_prefix = (
                None,
                None,
                None,
            )
            self.ibm_vpc_network = vpc
            db.session.add(self)
            db.session.commit()

            if public_gateway:
                self.ibm_public_gateway = public_gateway.add_update_db(vpc)
                db.session.commit()

            if network_acl:
                self.network_acl = network_acl.add_update_db(vpc)
                db.session.commit()

            if address_prefix:
                self.ibm_address_prefix = address_prefix.add_update_db(vpc)
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.zone = self.zone
            existing.region = self.region
            existing.resource_id = self.resource_id
            existing.ipv4_cidr_block = self.ipv4_cidr_block
            db.session.commit()

            network_acl, ibm_public_gateway, ibm_address_prefix = (
                self.network_acl,
                self.ibm_public_gateway,
                self.ibm_address_prefix,
            )

            self.network_acl, self.ibm_public_gateway, self.ibm_address_prefix = (
                None,
                None,
                None,
            )

            if network_acl:
                existing.network_acl = network_acl.add_update_db(vpc)
            else:
                existing.network_acl = None
            db.session.commit()

            if ibm_public_gateway:
                existing.ibm_public_gateway = ibm_public_gateway.add_update_db(vpc)
            else:
                existing.ibm_public_gateway = None
            db.session.commit()

            if ibm_address_prefix:
                existing.ibm_address_prefix = ibm_address_prefix.add_update_db(vpc)
            else:
                existing.ibm_address_prefix = None
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.REGION_KEY: self.region,
            self.ZONE_KEY: self.zone,
            self.IP_CIDR_BLOCK: self.ipv4_cidr_block,
            self.ACL_KEY: self.network_acl.to_json() if self.network_acl else "",
            self.VPC_KEY: {
                self.ID_KEY: self.ibm_vpc_network.id,
                self.NAME_KEY: self.ibm_vpc_network.name,
            }
            if self.ibm_vpc_network
            else None,
            self.PUBLIC_GATEWAY: self.ibm_public_gateway.id
            if self.ibm_public_gateway
            else None,
            self.ADDRESS_PREFIX_KEY: self.ibm_address_prefix.to_json()
            if self.ibm_address_prefix
            else "",
            self.CLOUD_ID_KEY: self.cloud_id,
        }

    def to_json_body(self):
        obj = {
            "name": self.name,
            "ip_version": "ipv4",
            "ipv4_cidr_block": self.ipv4_cidr_block,
            "zone": {"name": self.zone},
            "vpc": {"id": self.ibm_vpc_network.resource_id}
            if self.ibm_vpc_network
            else "",
            "public_gateway": {"id": self.ibm_public_gateway.resource_id}
            if self.ibm_public_gateway
            else None,
            "network_acl": {"id": self.network_acl.resource_id}
            if self.network_acl
            else None,
        }
        if self.ibm_resource_group:
            obj["resource_group"] = {"id": self.ibm_resource_group.resource_id}
        return obj

    def to_report_json(self, public_gateway=None):
        json_data = {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }
        if public_gateway:
            json_data.update({"public_gateway": public_gateway})

        return json_data

    @classmethod
    def from_ibm_json_body(cls, region, json_body):
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
        ibm_subnet = IBMSubnet(
            name=json_body["name"], zone=json_body["zone"]["name"], ipv4_cidr_block=json_body.get("ipv4_cidr_block"),
            region=region, resource_id=json_body["id"], status=status
        )

        return ibm_subnet
