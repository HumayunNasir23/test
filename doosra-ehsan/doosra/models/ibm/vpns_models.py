import json
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import CREATION_PENDING, CREATED, PENDING


class IBMIKEPolicy(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    DH_GROUP_KEY = "dh_group"
    ENCRYPTION_ALGORITHM_KEY = "encryption_algorithm"
    AUTHENTICATION_ALGORITHM_KEY = "authentication_algorithm"
    KEY_LIFETIME_KEY = "key_lifetime"
    IKE_VERSION_KEY = "ike_version"
    RESOURCE_GROUP_KEY = "resource_group"
    STATUS_KEY = "status"
    REGION_KEY = "region"
    CLOUD_ID_KEY = "cloud_id"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_ike_policy"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    region = Column(String(255), nullable=False)
    status = Column(String(50))
    ike_version = Column(Integer, default=2)
    key_lifetime = Column(Integer, default=28800)
    authentication_algorithm = Column(Enum("md5", "sha1", "sha256"), default="sha1")
    encryption_algorithm = Column(Enum("triple_des", "aes128", "aes256"), default="aes128")
    dh_group = Column(Integer, default=2)
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"))
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))
    vpn_connections = relationship(
        "IBMVpnConnection", backref="ibm_ike_policy", lazy="dynamic"
    )
    __table_args__ = (
        UniqueConstraint(name, region, cloud_id,
                         name="uix_ibm_ike_policy_name_region_cloud_id"),
    )

    def __init__(
        self,
        name,
        region,
        key_lifetime=None,
        status=CREATION_PENDING,
        ike_version=None,
        authentication_algorithm=None,
        encryption_algorithm=None,
        dh_group=None,
        resource_id=None,
        cloud_id=None,

    ):
        self.id = uuid.uuid4().hex
        self.name = name
        self.region = region
        self.status = status
        self.ike_version = ike_version
        self.authentication_algorithm = authentication_algorithm
        self.encryption_algorithm = encryption_algorithm
        self.key_lifetime = key_lifetime
        self.dh_group = dh_group
        self.resource_id = resource_id
        self.cloud_id = cloud_id

    def make_copy(self):
        obj = IBMIKEPolicy(
            name=self.name,
            region=self.region,
            key_lifetime=self.key_lifetime,
            status=self.status,
            ike_version=self.ike_version,
            authentication_algorithm=self.authentication_algorithm,
            encryption_algorithm=self.encryption_algorithm,
            dh_group=self.dh_group,
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
            and (self.resource_id == other.resource_id)
            and (self.ike_version == other.ike_version)
            and (self.key_lifetime == other.key_lifetime)
            and (self.authentication_algorithm == other.authentication_algorithm)
            and (self.encryption_algorithm == other.encryption_algorithm)
            and (self.dh_group == other.dh_group)
            and (self.status == other.status)
        ):
            return False
        if (self.ibm_resource_group and not other.ibm_resource_group) or (
            not self.ibm_resource_group and other.ibm_resource_group
        ):
            return False
        if self.ibm_resource_group and other.ibm_resource_group:
            if not self.ibm_resource_group.params_eq(other.ibm_resource_group):
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
            existing.region = self.region
            existing.status = self.status
            existing.resource_id = self.resource_id
            existing.ike_version = self.ike_version
            existing.key_lifetime = self.key_lifetime
            existing.authentication_algorithm = self.authentication_algorithm
            existing.encryption_algorithm = self.encryption_algorithm
            existing.dh_group = self.dh_group
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
            self.REGION_KEY: self.region,
            self.AUTHENTICATION_ALGORITHM_KEY: self.authentication_algorithm,
            self.ENCRYPTION_ALGORITHM_KEY: self.encryption_algorithm,
            self.KEY_LIFETIME_KEY: self.key_lifetime,
            self.IKE_VERSION_KEY: self.ike_version,
            self.DH_GROUP_KEY: self.dh_group,
            self.STATUS_KEY: self.status,
            self.RESOURCE_GROUP_KEY: self.ibm_resource_group.to_json()
            if self.ibm_resource_group
            else "",
            self.CLOUD_ID_KEY: self.cloud_id,
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "authentication_algorithm": self.authentication_algorithm,
            "encryption_algorithm": self.encryption_algorithm,
            "key_lifetime": self.key_lifetime,
            "ike_version": self.ike_version,
            "dh_group": self.dh_group,
            "resource_group": {
                "id": self.ibm_resource_group.resource_id
                if self.ibm_resource_group
                else ""
            },
        }

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }

    @classmethod
    def from_ibm_json_body(cls, region, json_body):
        # TODO: Verify Schema
        ibm_ike_policy = IBMIKEPolicy(
            name=json_body["name"],
            region=region,
            key_lifetime=json_body["key_lifetime"],
            status="CREATED",
            ike_version=json_body["ike_version"],
            authentication_algorithm=json_body["authentication_algorithm"],
            encryption_algorithm=json_body["encryption_algorithm"],
            dh_group=json_body["dh_group"],
            resource_id=json_body["id"],
        )

        return ibm_ike_policy


class IBMIPSecPolicy(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    REGION_KEY = "region"
    STATUS_KEY = "status"
    PFS_KEY = "pfs"
    DH_GROUP_KEY = "dh_group"
    ENCRYPTION_ALGORITHM_KEY = "encryption_algorithm"
    AUTHENTICATION_ALGORITHM_KEY = "authentication_algorithm"
    KEY_LIFETIME_KEY = "key_lifetime"
    RESOURCE_GROUP_KEY = "resource_group"
    CLOUD_ID_KEY = "cloud_id"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_ipsec_policy"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    region = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    authentication_algorithm = Column(
        Enum("md5", "sha1", "sha256"), default="sha1", nullable=False
    )
    encryption_algorithm = Column(
        Enum("triple_des", "aes128", "aes256"), default="aes128", nullable=False
    )
    pfs_dh_group = Column(
        Enum("group_2", "group_5", "group_14", "disabled"),
        default="disabled",
        nullable=False,
    )
    key_lifetime = Column(Integer, default=28800, nullable=False)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"))
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    vpn_connections = relationship(
        "IBMVpnConnection", backref="ibm_ipsec_policy", lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint(name, region, cloud_id,
                         name="uix_ibm_ipsec_policy_name_region_cloud_id"),
    )

    def __init__(
        self,
        name,
        region,
        key_lifetime=None,
        status=CREATION_PENDING,
        authentication_algorithm=None,
        encryption_algorithm=None,
        pfs_dh_group=None,
        resource_id=None,
        cloud_id=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.status = status
        self.authentication_algorithm = authentication_algorithm
        self.encryption_algorithm = encryption_algorithm
        self.key_lifetime = key_lifetime
        self.pfs_dh_group = pfs_dh_group
        self.resource_id = resource_id
        self.cloud_id = cloud_id

    def make_copy(self):
        obj = IBMIPSecPolicy(
            name=self.name,
            region=self.region,
            key_lifetime=self.key_lifetime,
            status=self.status,
            authentication_algorithm=self.authentication_algorithm,
            encryption_algorithm=self.encryption_algorithm,
            pfs_dh_group=self.pfs_dh_group,
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
            and (self.resource_id == other.resource_id)
            and (self.authentication_algorithm == other.authentication_algorithm)
            and (self.encryption_algorithm == other.encryption_algorithm)
            and (self.pfs_dh_group == other.pfs_dh_group)
            and (self.key_lifetime == other.key_lifetime)
            and (self.status == other.status)
            and (self.region == other.region)
        ):
            return False

        if (self.ibm_resource_group and not other.ibm_resource_group) or (
            not self.ibm_resource_group and other.ibm_resource_group
        ):
            return False

        if self.ibm_resource_group and other.ibm_resource_group:
            if not self.ibm_resource_group.params_eq(other.ibm_resource_group):
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
            existing.region = self.region
            existing.status = self.status
            existing.resource_id = self.resource_id
            existing.key_lifetime = self.key_lifetime
            existing.authentication_algorithm = self.authentication_algorithm
            existing.encryption_algorithm = self.encryption_algorithm
            existing.pfs_dh_group = self.pfs_dh_group
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
        json_data = {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.REGION_KEY: self.region,
            self.STATUS_KEY: self.status,
            self.AUTHENTICATION_ALGORITHM_KEY: self.authentication_algorithm,
            self.ENCRYPTION_ALGORITHM_KEY: self.encryption_algorithm,
            self.KEY_LIFETIME_KEY: self.key_lifetime,
            self.RESOURCE_GROUP_KEY: self.ibm_resource_group.to_json()
            if self.ibm_resource_group
            else "",
            self.CLOUD_ID_KEY: self.cloud_id,
        }

        if self.pfs_dh_group != "disabled":
            json_data[self.PFS_KEY] = "enabled"
            json_data[self.DH_GROUP_KEY] = self.pfs_dh_group
        else:
            json_data[self.PFS_KEY] = "disabled"

        return json_data

    def to_json_body(self):
        return {
            "name": self.name,
            "authentication_algorithm": self.authentication_algorithm,
            "encryption_algorithm": self.encryption_algorithm,
            "key_lifetime": self.key_lifetime,
            "pfs": self.pfs_dh_group,
            "resource_group": {
                "id": self.ibm_resource_group.resource_id
                if self.ibm_resource_group
                else ""
            },
        }

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }

    @classmethod
    def from_ibm_json_body(cls, region, json_body):
        ibm_ipsec_policy = IBMIPSecPolicy(
            name=json_body["name"],
            region=region,
            key_lifetime=json_body["key_lifetime"],
            status="CREATED",
            authentication_algorithm=json_body["authentication_algorithm"],
            encryption_algorithm=json_body["encryption_algorithm"],
            pfs_dh_group=json_body["pfs"],
            resource_id=json_body["id"],
        )

        return ibm_ipsec_policy


class IBMVpnGateway(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    REGION_KEY = "region"
    SUBNET_KEY = "subnet"
    CREATED_AT_KEY = "created_at"
    CONNECTIONS_KEY = "connections"
    VPC_KEY = "vpc"
    RESOURCE_GROUP_KEY = "resource_group"
    IP_ADDRESS_KEY = "ip_address"
    LOCATION_KEY = "location"
    GATEWAY_STATUS_KEY = "gateway_status"
    STATUS_KEY = "status"
    CLOUD_ID_KEY = "cloud_id"
    MESSAGE_KEY = "message"

    gateway_location = {
        "eu-de": "Frankfurt",
        "us-south": "Dallas",
        "eu-gb": "London",
        "jp-tok": "Tokyo",
        "au-syd": "Sydney",
    }

    __tablename__ = "ibm_vpn_gateways"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    public_ip = Column(String(16))
    region = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=True)
    gateway_status = Column(String(100), nullable=True)

    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    subnet_id = Column(String(32), ForeignKey("ibm_subnets.id"))
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    vpn_connections = relationship(
        "IBMVpnConnection",
        backref="ibm_vpn_gateway",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(
            name, vpc_id, cloud_id, name="uix_ibm_vpn_gateway_vpc_cloud_id"
        ),
    )

    def __init__(
        self,
        name,
        region=None,
        status=None,
        resource_id=None,
        public_ip=None,
        created_at=None,
        gateway_status=None,
        cloud_id=None,
        vpc_id=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = status or CREATION_PENDING
        self.public_ip = public_ip
        self.created_at = created_at
        self.region = region
        self.gateway_status = gateway_status
        self.resource_id = resource_id
        self.cloud_id = cloud_id
        self.vpc_id = vpc_id

    def make_copy(self):
        obj = IBMVpnGateway(
            name=self.name,
            region=self.region,
            status=self.status,
            resource_id=self.resource_id,
            public_ip=self.public_ip,
            created_at=self.created_at,
            gateway_status=self.gateway_status,
            cloud_id=self.cloud_id,
        )

        if self.ibm_resource_group:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()

        if self.ibm_subnet:
            obj.ibm_subnet = self.ibm_subnet.make_copy()

        for vpn_connection in self.vpn_connections.all():
            obj.vpn_connections.append(vpn_connection.make_copy())

        return obj

    def get_existing_from_db(self, vpc=None):
        if vpc:
            return (
                db.session.query(self.__class__)
                .filter_by(name=self.name, cloud_id=self.cloud_id, vpc_id=vpc.id)
                .first()
            )
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, cloud_id=self.cloud_id, vpc_id=self.vpc_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.resource_id == other.resource_id)
            and (self.public_ip == other.public_ip)
            and (self.region == other.region)
            and (self.gateway_status == other.gateway_status)
            and (self.status == other.status)
        ):
            return False

        if not len(self.vpn_connections.all()) == len(other.vpn_connections.all()):
            return False

        for vpn_connection in self.vpn_connections.all():
            found = False
            for vpn_connection_ in other.vpn_connections.all():
                if vpn_connection.params_eq(vpn_connection_):
                    found = True

            if not found:
                return False

        if (self.ibm_subnet and not other.ibm_subnet) or (
            not self.ibm_subnet and other.ibm_subnet
        ):
            return False

        if self.ibm_subnet and other.ibm_subnet:
            if not self.ibm_subnet.params_eq(other.ibm_subnet):
                return False

        if (self.ibm_resource_group and not other.ibm_resource_group) or (
            not self.ibm_resource_group and other.ibm_resource_group
        ):
            return False

        if self.ibm_resource_group and other.ibm_resource_group:
            if not self.ibm_resource_group.params_eq(other.ibm_resource_group):
                return False

        return True

    def add_update_db(self, vpc):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            vpn_connections, ibm_subnet, ibm_resource_group = (
                self.vpn_connections.all(),
                self.ibm_subnet,
                self.ibm_resource_group,
            )
            self.vpn_connections, self.ibm_subnet, self.ibm_resource_group = (
                list(),
                None,
                None,
            )
            self.ibm_vpc_network = vpc
            db.session.add(self)
            db.session.commit()

            if ibm_subnet:
                self.ibm_subnet = ibm_subnet.add_update_db(vpc)
                db.session.commit()

            if ibm_resource_group:
                self.ibm_resource_group = ibm_resource_group.add_update_db()
                db.session.commit()

            for vpn_connection in vpn_connections:
                vpn_connection.add_update_db(self)
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.resource_id = self.resource_id
            existing.public_ip = self.public_ip
            existing.region = self.region
            existing.gateway_status = self.gateway_status
            db.session.commit()

            for vpn_connection in existing.vpn_connections.all():
                found = False
                for vpn_connection_ in self.vpn_connections.all():
                    if vpn_connection.name == vpn_connection_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(vpn_connection)
                    db.session.commit()

            vpn_connections = self.vpn_connections.all()
            ibm_subnet, ibm_resource_group = self.ibm_subnet, self.ibm_resource_group
            self.vpn_connections, self.ibm_subnet, self.ibm_resource_group = (
                list(),
                None,
                None,
            )

            for vpn_connection in vpn_connections:
                vpn_connection.add_update_db(existing)
                db.session.commit()

            if ibm_subnet:
                existing.ibm_subnet = ibm_subnet.add_update_db(vpc)
            else:
                existing.ibm_subnet = None
            db.session.commit()

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
            self.REGION_KEY: self.region,
            self.SUBNET_KEY: self.ibm_subnet.to_json() if self.ibm_subnet else "",
            self.CREATED_AT_KEY: self.created_at,
            self.RESOURCE_GROUP_KEY: self.ibm_resource_group.to_json()
            if self.ibm_resource_group
            else "",
            self.VPC_KEY: {
                self.ID_KEY: self.ibm_vpc_network.id,
                self.NAME_KEY: self.ibm_vpc_network.name,
            }
            if self.ibm_vpc_network
            else None,
            self.IP_ADDRESS_KEY: self.public_ip,
            self.GATEWAY_STATUS_KEY: self.gateway_status,
            self.STATUS_KEY: self.status,
            self.LOCATION_KEY: self.gateway_location[self.region]
            if self.region in self.gateway_location.keys()
            else self.region,
            self.CONNECTIONS_KEY: [
                connection.to_json() for connection in self.vpn_connections.all()
            ],
            self.CLOUD_ID_KEY: self.cloud_id,
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "subnet": {"id": self.ibm_subnet.resource_id if self.ibm_subnet else ""},
            "resource_group": {
                "id": self.ibm_resource_group.resource_id
                if self.ibm_resource_group
                else ""
            },
        }

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }

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
        ibm_vpn_gateway = IBMVpnGateway(
            name=json_body["name"], region=region, resource_id=json_body["id"],
            public_ip=json_body["public_ip"]["address"], created_at=json_body["created_at"],
            gateway_status=json_body["status"]
        )

        return ibm_vpn_gateway


class IBMVpnConnection(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    GATEWAY_ADDRESS_KEY = "gateway_ip"
    CREATED_AT_KEY = "created_at"
    PEER_ADDRESS_KEY = "peer_address"
    LOCAL_CIDRS_KEY = "local_cidrs"
    PEER_CIDRS_KEY = "peer_cidrs"
    PSK_KEY = "pre_shared_secret"
    DPD_ACTION_KEY = "action"
    DPD_INTERVAL_KEY = "interval"
    DPD_TIMEOUT_KEY = "timeout"
    VPN_STATUS_KEY = "vpn_status"
    ROUTE_MODE_KEY = "route_mode"
    ADMIN_STATE_UP_KEY = "admin_state_up"
    DEAD_PEER_DETECTION_KEY = "dead_peer_detection"
    IKE_POLICY = "ike_policy"
    IPSEC_POLICY = "ipsec_policy"
    DISCOVERED_LOCAL_CIDRS = "discovered_local_cidrs"
    AUTHENTICATION_MODE = "authentication_mode"
    STATUS_KEY = "status"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_vpn_connections"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=True)
    # Check why local_address is required
    local_address = Column(String(255), nullable=True)
    peer_address = Column(String(255), nullable=False)
    pre_shared_key = Column(String(255), nullable=False)
    # TODO: make it a property, and convert to string while storing and list while retrieving
    local_cidrs = Column(Text, nullable=False)
    peer_cidrs = Column(Text, nullable=False)
    dpd_action = Column(
        Enum("restart", "clear", "hold", "none"), default="restart", nullable=False
    )
    dpd_interval = Column(Integer, default=30, nullable=False)
    dpd_timeout = Column(Integer, default=120, nullable=False)
    admin_state_up = Column(Boolean, nullable=False, default=True)
    authentication_mode = Column(String(100), nullable=False, default="psk")
    vpn_status = Column(String(10), nullable=False, default="down")
    route_mode = Column(String(100), nullable=True)
    discovered_local_cidrs = Column(Text, nullable=True)

    ike_policy_id = Column(String(32), ForeignKey("ibm_ike_policy.id"), nullable=True)
    ipsec_policy_id = Column(
        String(32), ForeignKey("ibm_ipsec_policy.id"), nullable=True
    )
    vpn_gateway_id = Column(
        String(32),
        ForeignKey("ibm_vpn_gateways.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            name, vpn_gateway_id, name="uix_ibm_vpn_connection_name_vpn_gateway_id"
        ),
    )

    def __init__(
        self,
        name,
        peer_address=None,
        pre_shared_key=None,
        local_cidrs=None,
        peer_cidrs=None,
        dpd_interval=None,
        dpd_timeout=None,
        local_address=None,
        dpd_action=None,
        status=None,
        resource_id=None,
        route_mode=None,
        admin_state_up=True,
        authentication_mode=None,
        created_at=None,
        vpn_status=None,
        vpn_gateway_id=None,
        discovered_local_cidrs=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = status or CREATION_PENDING
        self.local_address = local_address
        self.peer_address = peer_address
        self.pre_shared_key = pre_shared_key
        self.local_cidrs = local_cidrs
        self.peer_cidrs = peer_cidrs
        self.dpd_action = dpd_action or "restart"
        self.dpd_interval = dpd_interval or 30
        self.dpd_timeout = dpd_timeout or 120
        self.admin_state_up = admin_state_up
        self.created_at = created_at
        self.authentication_mode = authentication_mode or "psk"
        self.resource_id = resource_id
        self.vpn_status = vpn_status or "down"
        self.route_mode = route_mode
        self.vpn_gateway_id = vpn_gateway_id
        self.discovered_local_cidrs = discovered_local_cidrs

    def make_copy(self):
        obj = IBMVpnConnection(
            name=self.name,
            peer_address=self.peer_address,
            pre_shared_key=self.pre_shared_key,
            local_cidrs=self.local_cidrs,
            peer_cidrs=self.peer_cidrs,
            dpd_interval=self.dpd_interval,
            dpd_timeout=self.dpd_timeout,
            local_address=self.local_address,
            dpd_action=self.dpd_action,
            status=self.status,
            resource_id=self.resource_id,
            route_mode=self.route_mode,
            admin_state_up=self.admin_state_up,
            authentication_mode=self.authentication_mode,
            created_at=self.created_at,
            vpn_status=self.vpn_status,
        )

        if self.ibm_ike_policy:
            obj.ibm_ike_policy = self.ibm_ike_policy.make_copy()

        if self.ibm_ipsec_policy:
            obj.ibm_ipsec_policy = self.ibm_ipsec_policy.make_copy()

        return obj

    def get_existing_from_db(self, vpn_gateway=None):
        if vpn_gateway:
            return (
                db.session.query(self.__class__)
                .filter_by(name=self.name, vpn_gateway_id=vpn_gateway.id)
                .first()
            )
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, vpn_gateway_id=self.vpn_gateway_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.resource_id == other.resource_id)
            and (self.peer_address == other.peer_address)
            and (self.pre_shared_key == other.pre_shared_key)
            and (self.dpd_action == other.dpd_action)
            and (self.dpd_interval == other.dpd_interval)
            and (self.dpd_timeout == other.dpd_timeout)
            and (self.admin_state_up == other.admin_state_up)
            and (self.authentication_mode == other.authentication_mode)
            and (self.vpn_status == other.vpn_status)
            and (self.route_mode == other.route_mode)
            and (set(self.local_cidrs) == set(other.local_cidrs))
            and (set(self.peer_cidrs) == set(other.peer_cidrs))
            and (self.status == other.status)
        ):
            return False

        if (self.ibm_ike_policy and not other.ibm_ike_policy) or (
            not self.ibm_ike_policy and other.ibm_ike_policy
        ):
            return False

        if self.ibm_ike_policy and other.ibm_ike_policy:
            if not self.ibm_ike_policy.params_eq(other.ibm_ike_policy):
                return False

        if (self.ibm_ipsec_policy and not other.ibm_ipsec_policy) or (
            not self.ibm_ipsec_policy and other.ibm_ipsec_policy
        ):
            return False

        if self.ibm_ipsec_policy and other.ibm_ipsec_policy:
            if not self.ibm_ipsec_policy.params_eq(other.ibm_ipsec_policy):
                return False

        return True

    def add_update_db(self, vpn_gateway):
        existing = self.get_existing_from_db(vpn_gateway)
        if not existing:
            ike_policy, ipsec_policy = self.ibm_ike_policy, self.ibm_ipsec_policy
            self.ibm_ike_policy, self.ibm_ipsec_policy = None, None
            self.ibm_vpn_gateway = vpn_gateway
            db.session.add(self)
            db.session.commit()

            if ike_policy:
                self.ibm_ike_policy = ike_policy.add_update_db()
                db.session.commit()

            if ipsec_policy:
                self.ibm_ipsec_policy = ipsec_policy.add_update_db()
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.resource_id = self.resource_id
            existing.peer_address = self.peer_address
            existing.pre_shared_key = self.pre_shared_key
            existing.dpd_action = self.dpd_action or "restart"
            existing.dpd_interval = self.dpd_interval or 30
            existing.dpd_timeout = self.dpd_timeout or 120
            existing.admin_state_up = self.admin_state_up
            existing.authentication_mode = self.authentication_mode or "psk"
            existing.vpn_status = self.vpn_status or "down"
            existing.route_mode = self.route_mode
            existing.local_cidrs = self.local_cidrs
            existing.peer_cidrs = self.peer_cidrs
            existing.discovered_local_cidrs = self.discovered_local_cidrs
            db.session.commit()

            ike_policy, ipsec_policy = self.ibm_ike_policy, self.ibm_ipsec_policy
            self.ibm_ike_policy, self.ibm_ipsec_policy = None, None
            if ike_policy:
                existing.ibm_ike_policy = ike_policy.add_update_db()
            else:
                existing.ibm_ike_policy = None
            db.session.commit()

            if ipsec_policy:
                existing.ibm_ipsec_policy = ipsec_policy.add_update_db()
            else:
                existing.ibm_ipsec_policy = None
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.GATEWAY_ADDRESS_KEY: self.local_address,
            self.PEER_ADDRESS_KEY: self.peer_address,
            self.LOCAL_CIDRS_KEY: json.loads(self.local_cidrs)
            if self.local_cidrs
            else [],
            self.PEER_CIDRS_KEY: json.loads(self.peer_cidrs) if self.peer_cidrs else [],
            self.PSK_KEY: self.pre_shared_key,
            self.VPN_STATUS_KEY: self.vpn_status,
            self.ROUTE_MODE_KEY: self.route_mode,
            self.CREATED_AT_KEY: self.created_at,
            self.ADMIN_STATE_UP_KEY: self.admin_state_up,
            self.DEAD_PEER_DETECTION_KEY: {
                self.DPD_ACTION_KEY: self.dpd_action,
                self.DPD_INTERVAL_KEY: self.dpd_interval,
                self.DPD_TIMEOUT_KEY: self.dpd_timeout,
            },
            self.IKE_POLICY: self.ibm_ike_policy.to_json()
            if self.ibm_ike_policy
            else "",
            self.IPSEC_POLICY: self.ibm_ipsec_policy.to_json()
            if self.ibm_ipsec_policy
            else "",
            self.DISCOVERED_LOCAL_CIDRS: self.discovered_local_cidrs,
            self.AUTHENTICATION_MODE: self.authentication_mode
        }

    def to_json_body(self):
        json_data = {
            "name": self.name,
            "peer_address": self.peer_address,
            "local_cidrs": json.loads(self.local_cidrs),
            "peer_cidrs": json.loads(self.peer_cidrs),
            "psk": self.pre_shared_key,
            "dead_peer_detection": {
                "action": str(self.dpd_action).lower(),
                "interval": self.dpd_interval,
                "timeout": self.dpd_timeout,
            },
        }

        if self.ibm_ike_policy:
            json_data["ike_policy"] = {"id": self.ibm_ike_policy.resource_id}

        if self.ibm_ipsec_policy:
            json_data["ipsec_policy"] = {"id": self.ibm_ipsec_policy.resource_id}

        return json_data

    def to_report_json(self, vpn):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: "",
            "vpn": "{vpn}.".format(vpn=vpn)
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        return IBMVpnConnection(
            name=json_body["name"], peer_address=json_body["peer_address"], pre_shared_key=json_body["psk"],
            local_cidrs=json.dumps(json_body["local_cidrs"]), peer_cidrs=json.dumps(json_body["peer_cidrs"]),
            dpd_interval=json_body["dead_peer_detection"]["interval"],
            dpd_timeout=json_body["dead_peer_detection"]["timeout"],
            dpd_action=json_body["dead_peer_detection"]["action"], status="CREATED", resource_id=json_body["id"],
            route_mode=json_body["route_mode"], admin_state_up=json_body["admin_state_up"],
            authentication_mode=json_body["authentication_mode"], created_at=json_body["created_at"],
            vpn_status=json_body["status"]
        )
