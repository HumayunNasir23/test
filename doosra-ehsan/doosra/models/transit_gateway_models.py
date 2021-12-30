import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    String,
)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import CREATION_PENDING


class TransitGateway(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    RESOURCE_GROUP_KEY = "resource_group"
    IS_GLOBAL_ROUTE_KEY = "is_global_route"
    REGION_KEY = "region"
    TYPE_KEY = "type"
    STATUS_KEY = "status"
    CRN_KEY = "crn"
    GATEWAY_STATUS_KEY = "gateway_status"
    CLOUD_ID_KEY = "cloud_id"
    CONNECTIONS_KEY = "connections"
    CREATED_AT_KEY = "created_at"

    __tablename__ = "transit_gateways"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    crn = Column(String(255), nullable=True)
    is_global_route = Column(Boolean, default=False, nullable=False)
    region = Column(String(255), nullable=False)
    type = Column(Enum("IBM"), default="IBM", nullable=False)
    status = Column(String(50))
    gateway_status = Column(Enum("available", "failed", "pending", "deleting"), default="pending")
    created_at = Column(String(255), nullable=True)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    connections = relationship(
        "TransitGatewayConnection",
        backref="transit_gateway",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __init__(
            self,
            name,
            region=None,
            type_=None,
            is_global_route=None,
            status=None,
            crn=None,
            gateway_status=None,
            resource_id=None,
            cloud_id=None,
            created_at=None,

    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.type = type_ or "IBM"
        self.is_global_route = is_global_route
        self.status = status or CREATION_PENDING
        self.crn = crn
        self.gateway_status = gateway_status
        self.resource_id = resource_id
        self.cloud_id = cloud_id
        self.created_at = created_at

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.REGION_KEY: self.region,
            self.TYPE_KEY: self.type,
            self.IS_GLOBAL_ROUTE_KEY: self.is_global_route,
            self.STATUS_KEY: self.status,
            self.CRN_KEY: self.crn,
            self.GATEWAY_STATUS_KEY: self.gateway_status,
            self.RESOURCE_GROUP_KEY: self.ibm_resource_group.to_json()
            if self.ibm_resource_group
            else "",
            self.CONNECTIONS_KEY: [
                connection.to_json() for connection in self.connections.all()
            ],
            self.CLOUD_ID_KEY: self.cloud_id,
            self.CREATED_AT_KEY: self.created_at,
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "location": self.region,
            "global": self.is_global_route,
            "resource_group": {
                "id": self.ibm_resource_group.resource_id
                if self.ibm_resource_group
                else None
            },
        }


class TransitGatewayConnection(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    VPC_KEY = "vpc"
    REGION_KEY = "region"
    RESOURCE_KEY = "resource_id"
    NETWORK_TYPE_KEY = "network_type"
    STATUS_KEY = "status"
    CONNECTION_STATUS = "connection_status"
    NETWORK_ID_KEY = "network_id"
    CREATED_AT_KEY = "created_at"

    __tablename__ = "transit_gateway_connections"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    region = Column(String(255), nullable=True)
    status = Column(String(50))
    connection_status = Column(Enum("attached", "failed", "pending", "deleting"), default="pending")
    network_type = Column(Enum("vpc", "classic"), default="vpc", nullable=False)
    network_id = Column(String(255), nullable=True)
    created_at = Column(String(255), nullable=True)

    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id", ondelete="CASCADE"))
    transit_gateway_id = Column(
        String(32),
        ForeignKey("transit_gateways.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            name, transit_gateway_id, name="uix_transit_connection_name_transit_gateway_id"
        ),
    )

    def __init__(
            self,
            name,
            region=None,
            network_type=None,
            network_id=None,
            status=None,
            connection_status=None,
            transit_gateway_id=None,
            resource_id=None,
            created_at=None,

    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.network_type = network_type
        self.network_id = network_id
        self.status = status or CREATION_PENDING
        self.connection_status = connection_status
        self.transit_gateway_id = transit_gateway_id
        self.resource_id = resource_id
        self.created_at = created_at

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.VPC_KEY:
                {
                    self.ID_KEY: self.ibm_vpc_network.id,
                    self.NAME_KEY: self.ibm_vpc_network.name,
                } if self.ibm_vpc_network else {},

            self.REGION_KEY: self.region,
            self.NETWORK_TYPE_KEY: self.network_type,
            self.STATUS_KEY: self.status,
            self.RESOURCE_KEY: self.resource_id,
            self.CONNECTION_STATUS: self.connection_status,
            self.NETWORK_ID_KEY: self.network_id if self.network_id else "",
            self.CREATED_AT_KEY: self.created_at,
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "network_type": self.network_type,
            "network_id": self.network_id if self.network_id else None,
        }
