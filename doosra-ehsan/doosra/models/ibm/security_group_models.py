import uuid

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    String,
)
from sqlalchemy import (
    Enum,
    Integer,
)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import CREATION_PENDING, PENDING


class IBMSecurityGroup(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    IS_DEFAULT_KEY = "is_default"
    REGION_KEY = "region"
    STATUS_KEY = "status"
    RESOURCE_ID_KEY = "resource_id"
    RULES_KEY = "rules"
    NETWORK_INTERFACES_KEY = "network_interfaces"
    CLOUD_ID_KEY = "cloud_id"
    RESOURCE_GROUP_KEY = "resource_group"
    VPC_KEY = "vpc"
    MESSAGE_KEY = "message"
    IS_ALLOW_ALL_KEY = "is_allow_all"

    __tablename__ = "ibm_security_groups"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    status = Column(String(50), nullable=False)
    region = Column(String(50), nullable=True)

    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    rules = relationship(
        "IBMSecurityGroupRule",
        backref="security_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(name, vpc_id, region,
                         name="uix_ibm_security_group_name_vpc_id_region"),
    )

    def __init__(
        self, name, region, resource_id=None, is_default=False, status=CREATION_PENDING, cloud_id=None, vpc_id=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.is_default = is_default
        self.status = status
        self.resource_id = resource_id
        self.cloud_id = cloud_id
        self.vpc_id = vpc_id

    @property
    def is_allow_all(self):
        allow_all_rules = [rule.is_inbound_allow_all and rule.is_outbound_allow_all for rule in self.rules.all()]
        return len(allow_all_rules) >= 2

    def make_copy(self):
        obj = IBMSecurityGroup(
            self.name, self.region, self.resource_id, self.is_default, self.status, self.cloud_id
        )
        for rule in self.rules:
            obj.rules.append(rule.make_copy())

        if self.ibm_resource_group:
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
            and (self.resource_id == other.resource_id)
            and (self.region == other.region)
            and (self.status == other.status)
        ):
            return False

        if not len(self.rules.all()) == len(other.rules.all()):
            return False

        for rule in self.rules.all():
            found = False
            for rule_ in other.rules.all():
                if rule.params_eq(rule_):
                    found = True

            if not found:
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
            resource_group = self.ibm_resource_group
            self.ibm_resource_group = None
            self.ibm_vpc_network = vpc
            db.session.add(self)
            db.session.commit()

            if resource_group:
                self.ibm_resource_group = resource_group.add_update_db()
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.region = self.region
            existing.status = self.status
            existing.resource_id = self.resource_id
            db.session.commit()

            for rule in existing.rules.all():
                found = False
                for rule_ in self.rules.all():
                    if rule.params_eq(rule_):
                        found = True
                        break

                if not found:
                    db.session.delete(rule)
                    db.session.commit()

            rules, resource_group = self.rules.all(), self.ibm_resource_group
            self.rules, self.ibm_resource_group = list(), None
            for rule in rules:
                rule.add_update_db(existing)
                db.session.commit()

            if resource_group:
                existing.ibm_resource_group = resource_group.add_update_db()
            else:
                existing.ibm_resource_group = None
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.IS_ALLOW_ALL_KEY: self.is_allow_all,
            self.IS_DEFAULT_KEY: self.is_default,
            self.REGION_KEY: self.region,
            self.STATUS_KEY: self.status,
            self.RULES_KEY: [rule.to_json() for rule in self.rules],
            self.NETWORK_INTERFACES_KEY: [
                interface.to_json() for interface in self.network_interfaces
            ],
            self.CLOUD_ID_KEY: self.cloud_id,
            self.RESOURCE_GROUP_KEY: self.ibm_resource_group.to_json()
            if self.ibm_resource_group
            else "",
            self.VPC_KEY: {
                self.ID_KEY: self.ibm_vpc_network.id,
                self.NAME_KEY: self.ibm_vpc_network.name,
            }
            if self.ibm_vpc_network
            else None,
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "vpc": {
                "id": self.ibm_vpc_network.resource_id if self.ibm_vpc_network else None
            },
            "rules": [rule.to_json_body() for rule in self.rules.all()],
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
        ibm_security_group = IBMSecurityGroup(
            name=json_body["name"], region=region, resource_id=json_body["id"], status="CREATED"
        )

        for rule in json_body["rules"]:
            ibm_security_group.rules.append(IBMSecurityGroupRule.from_ibm_json_body(rule))

        return ibm_security_group


class IBMSecurityGroupRule(db.Model):
    ID_KEY = "id"
    RESOURCE_ID_KEY = "resource_id"
    DIRECTION_KEY = "direction"
    PROTOCOL_KEY = "protocol"
    PORT_MAX_KEY = "port_max"
    PORT_MIN_KEY = "port_min"
    CIDR_BLOCK_KEY = "cidr_block"
    SECURITY_GROUP_KEY = "security_group"
    RULE_TYPE_KEY = "rule_type"
    ADDRESS_KEY = "address"
    CODE_KEY = "code"
    TYPE_KEY = "type"

    __tablename__ = "ibm_security_group_rules"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    status = Column(String(50), nullable=False)
    direction = Column(String(255), nullable=False)
    rule_type = Column(
        String(255),
        Enum("address", "any", "cidr_block", "security_group"),
        default="any",
    )
    protocol = Column(String(255), Enum("all", "icmp", "tcp", "udp"))
    cidr_block = Column(String(255))
    address = Column(String(255))
    port_max = Column(Integer)
    port_min = Column(Integer)
    code = Column(Integer)
    # TODO: Change to icmp type
    type = Column(Integer)

    security_group_id = Column(
        String(32), ForeignKey("ibm_security_groups.id"), nullable=False
    )

    def __init__(
        self,
        direction,
        protocol=None,
        code=None,
        type_=None,
        port_min=None,
        port_max=None,
        address=None,
        cidr_block=None,
        rule_type=None,
        resource_id=None,
        status=CREATION_PENDING,
    ):
        self.id = str(uuid.uuid4().hex)
        self.status = status
        self.resource_id = resource_id
        self.direction = direction
        self.protocol = protocol
        self.port_max = port_max
        self.port_min = port_min
        self.cidr_block = cidr_block
        self.address = address
        self.code = code
        self.type = type_
        self.rule_type = rule_type or "any"

    def make_copy(self):
        return IBMSecurityGroupRule(
            self.direction,
            self.protocol,
            self.code,
            self.type,
            self.port_min,
            self.port_max,
            self.address,
            self.cidr_block,
            self.rule_type,
            self.resource_id,
            self.status,
        )

    @property
    def _is_allow_all(self):
        return self.protocol == 'all' and self.rule_type == 'any'

    @property
    def is_inbound_allow_all(self):
        return self.direction == 'inbound' and self._is_allow_all

    @property
    def is_outbound_allow_all(self):
        return self.direction == 'outbound' and self._is_allow_all

    def get_existing_from_db(self, security_group=None):
        if security_group:
            return (
                db.session.query(self.__class__)
                    .filter_by(
                    port_max=self.port_max,
                    port_min=self.port_min,
                    direction=self.direction,
                    code=self.code,
                    type=self.type,
                    protocol=self.protocol,
                    rule_type=self.rule_type,
                    security_group_id=security_group.id,
                )
                    .first()
            )

        return (
            db.session.query(self.__class__)
                .filter_by(
                port_max=self.port_max,
                port_min=self.port_min,
                direction=self.direction,
                code=self.code,
                type=self.type,
                protocol=self.protocol,
                security_group_id=self.security_group_id,
            )
                .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.direction == other.direction)
            and (self.protocol == other.protocol)
            and (self.code == other.code)
            and (self.type == other.type)
            and (self.status == other.status)
            and (self.port_min == other.port_min)
            and (self.port_max == other.port_max)
            and (self.address == other.address)
            and (self.cidr_block == other.cidr_block)
            and (self.rule_type == other.rule_type)
            and (self.resource_id == other.resource_id)
        ):
            return False
        return True

    def add_update_db(self, security_group):
        existing = self.get_existing_from_db(security_group)
        if not existing:
            self.security_group = security_group
            db.session.add(self)
            db.session.commit()
            return self

        if not self.params_eq(existing):
            existing.status = self.status
            existing.direction = self.direction
            existing.protocol = self.protocol
            existing.code = self.code
            existing.type = self.type
            existing.port_min = self.port_min
            existing.port_max = self.port_max
            existing.address = self.address
            existing.cidr_block = self.cidr_block
            existing.rule_type = self.rule_type
            existing.resource_id = self.resource_id
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.DIRECTION_KEY: self.direction,
            self.PROTOCOL_KEY: self.protocol,
            self.PORT_MAX_KEY: self.port_max,
            self.PORT_MIN_KEY: self.port_min,
            self.RULE_TYPE_KEY: self.rule_type,
            self.CIDR_BLOCK_KEY: self.cidr_block,
            self.ADDRESS_KEY: self.address,
            self.CODE_KEY: self.code,
            self.TYPE_KEY: self.type,
            self.SECURITY_GROUP_KEY: self.security_group.name
            if self.security_group and self.rule_type == "security_group"
            else None,
        }

    def to_json_body(self):
        json_data = {
            "direction": self.direction,
            "ip_version": "ipv4",
            "protocol": self.protocol,
        }

        if self.protocol in ["tcp", "udp"]:
            json_data["port_max"] = self.port_max
            json_data["port_min"] = self.port_min

        elif self.protocol == "icmp":
            json_data["code"] = self.code
            json_data["type"] = self.type

        if self.rule_type == "security_group":
            json_data["remote"] = {"id": self.security_group.resource_id}

        elif self.cidr_block:
            json_data["remote"] = {"cidr_block": self.cidr_block}

        elif self.address:
            json_data["remote"] = {"address": self.address}

        return json_data

    @classmethod
    def from_ibm_json_body(cls, json_body):
        ibm_security_group_rule = IBMSecurityGroupRule(
            direction=json_body["direction"],
            protocol=json_body.get("protocol", "all"),
            resource_id=json_body.get("id"),
            status="CREATED",
        )

        if ibm_security_group_rule.protocol == "icmp":
            ibm_security_group_rule.type = json_body.get("type")
            if ibm_security_group_rule.type:
                ibm_security_group_rule.code = json_body.get("code")

        elif ibm_security_group_rule.protocol in ["tcp", "udp"]:
            ibm_security_group_rule.port_min = json_body.get("port_min")
            ibm_security_group_rule.port_max = json_body.get("port_max")

        # any or cidr block
        if json_body["remote"].get("cidr_block"):
            cidr_block = json_body["remote"]["cidr_block"]
            ibm_security_group_rule.rule_type = "any" if cidr_block == "0.0.0.0/0" else "cidr_block"
            ibm_security_group_rule.cidr_block = cidr_block
        elif json_body["remote"].get("address"):
            ibm_security_group_rule.rule_type = "address"
            ibm_security_group_rule.address = json_body["remote"]["address"]
        elif json_body["remote"].get("name"):
            # TODO: Create a relation for security group which is associated
            ibm_security_group_rule.rule_type = "security_group"

        return ibm_security_group_rule
