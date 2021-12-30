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


class IBMNetworkAcl(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    REGION_KEY = "region"
    RESOURCE_ID_KEY = "resource_id"
    RULES_KEY = "rules"
    CLOUD_ID_KEY = "cloud_id"
    IS_DEFAULT_KEY = "is_default"
    VPC_ID_KEY = "vpc_id"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_network_acls"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    region = Column(String(50))
    is_default = Column(Boolean, default=False, nullable=False)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=True)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    rules = relationship(
        "IBMNetworkAclRule",
        backref="ibm_network_acl",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    subnets = relationship("IBMSubnet", backref="network_acl", lazy="dynamic")

    __table_args__ = (
        UniqueConstraint(
            name, region, vpc_id, cloud_id, name="uix_ibm_acl_name_vpc_region_cloud_id"
        ),
    )

    def __init__(
        self,
        name,
        region=None,
        resource_id=None,
        status=CREATION_PENDING,
        cloud_id=None,
        is_default=False,
        vpc_id=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.is_default = is_default
        self.status = status
        self.region = region
        self.resource_id = resource_id
        self.cloud_id = cloud_id
        self.vpc_id = vpc_id

    def add_rule(self, rule):
        for rule_ in self.rules.all():
            rule_name = rule.name
            rule.name = rule_.name
            if rule.params_eq(rule_):
                return

            rule.name = rule_name
        self.rules.append(rule)

    def make_copy(self):
        obj = IBMNetworkAcl(
            self.name,
            self.region,
            self.resource_id,
            self.status,
            self.cloud_id,
            self.is_default,
        )
        for rule in self.rules.all():
            obj.rules.append(rule.make_copy())

        if self.resource_group_id:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()
        return obj

    def get_existing_from_db(self, vpc=None):
        if vpc:
            return (
                db.session.query(self.__class__)
                .filter_by(name=self.name, vpc_id=vpc.id, cloud_id=self.cloud_id, region=self.region)
                .first()
            )
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, vpc_id=self.vpc_id, cloud_id=self.cloud_id, region=self.region)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.region == other.region)
            and (self.resource_id == other.resource_id)
            and (self.is_default == other.is_default)
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

        return True

    def add_update_db(self, vpc):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            rules = self.rules.all()
            self.rules = list()
            self.ibm_vpc_network = vpc
            db.session.add(self)
            db.session.commit()

            for rule in rules:
                rule.add_update_db(self)

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.region = self.region
            existing.is_default = self.is_default
            existing.status = self.status
            existing.resource_id = self.resource_id
            db.session.commit()

            for rule in existing.rules.all():
                found = False
                for rule_ in self.rules.all():
                    if rule.name == rule_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(rule)
                    db.session.commit()

            rules = self.rules.all()
            self.rules = list()
            for rule in rules:
                rule.add_update_db(existing)
                db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.CLOUD_ID_KEY: self.cloud_id,
            self.IS_DEFAULT_KEY: self.is_default,
            self.REGION_KEY: self.region,
            self.STATUS_KEY: self.status,
            self.RULES_KEY: [rule.to_json() for rule in self.rules.all()],
            self.VPC_ID_KEY: self.vpc_id
        }

    def to_json_body(self):
        obj = {
            "name": self.name,
            "rules": [rule.to_json_body() for rule in self.rules.all()],
            "vpc": {
                "id": self.ibm_vpc_network.resource_id if self.ibm_vpc_network else ""
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
        # TODO: Check schema. Investigate resource_id = None for rules
        ibm_network_acl = IBMNetworkAcl(
            name=json_body["name"], region=region, resource_id=json_body["id"], status="CREATED"
        )
        for rule in json_body.get("rules", []):
            ibm_network_acl.rules.append(IBMNetworkAclRule.from_ibm_json_body(rule))

        return ibm_network_acl


class IBMNetworkAclRule(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    RESOURCE_ID_KEY = "resource_id"
    ACTION_KEY = "action"
    DESTINATION_KEY = "destination"
    DIRECTION_KEY = "direction"
    SOURCE_KEY = "source"
    PROTOCOL_KEY = "protocol"
    DESTINATION_PORT_MAX_KEY = "destination_port_max"
    DESTINATION_PORT_MIN_KEY = "destination_port_min"
    SOURCE_PORT_MAX_KEY = "source_port_max"
    SOURCE_PORT_MIN_KEY = "source_port_min"
    CODE_KEY = "code"
    TYPE_KEY = "type"

    __tablename__ = "ibm_network_acl_rules"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    action = Column(String(255), nullable=False)
    protocol = Column(String(255), Enum("tcp", "udp", "icmp", "all"), nullable=False)
    direction = Column(String(255), nullable=False)
    destination = Column(String(255))
    source = Column(String(255))
    port_max = Column(Integer)
    port_min = Column(Integer)
    source_port_max = Column(Integer)
    source_port_min = Column(Integer)
    code = Column(Integer)
    type = Column(Integer)

    acl_id = Column(String(32), ForeignKey("ibm_network_acls.id"), nullable=False)

    __table_args__ = (UniqueConstraint(name, acl_id, name="uix_ibm_acl_name_acl_id"),)

    def __init__(
        self,
        name,
        action,
        destination=None,
        direction=None,
        source=None,
        protocol=None,
        port_max=None,
        port_min=None,
        source_port_max=None,
        source_port_min=None,
        code=None,
        type_=None,
        resource_id=None,
        status=CREATION_PENDING,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.resource_id = resource_id
        self.status = status
        self.action = action
        self.direction = direction
        self.destination = destination
        self.source = source
        self.protocol = protocol
        self.port_min = port_min  # destination_port_min
        self.port_max = port_max  # destination_port_max
        self.source_port_min = source_port_min
        self.source_port_max = source_port_max
        self.code = code
        self.type = type_

    def make_copy(self):
        return IBMNetworkAclRule(
            self.name,
            self.action,
            self.destination,
            self.direction,
            self.source,
            self.protocol,
            self.port_max,
            self.port_min,
            self.source_port_max,
            self.source_port_min,
            self.code,
            self.type,
            self.resource_id,
            self.status,
        )

    def get_existing_from_db(self, ibm_network_acl=None):
        if ibm_network_acl:
            return (
                db.session.query(self.__class__)
                .filter_by(name=self.name, acl_id=ibm_network_acl.id)
                .first()
            )
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, acl_id=self.acl_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.destination == other.destination)
            and (self.action == other.action)
            and (self.direction == other.direction)
            and (self.source == other.source)
            and (self.protocol == other.protocol)
            and (self.port_max == other.port_max)
            and (self.port_min == other.port_min)
            and (self.source_port_max == other.source_port_max)
            and (self.source_port_min == other.source_port_min)
            and (self.code == other.code)
            and (self.type == other.type)
            and (self.resource_id == other.resource_id)
            and (self.status == other.status)
        ):
            return False

        return True

    def add_update_db(self, ibm_network_acl):
        existing = self.get_existing_from_db(ibm_network_acl)
        if not existing:
            self.ibm_network_acl = ibm_network_acl
            db.session.add(self)
            db.session.commit()
            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.destination = self.destination
            existing.action = self.action
            existing.direction = self.direction
            existing.source = self.source
            existing.protocol = self.protocol
            existing.port_max = self.port_max
            existing.port_min = self.port_min
            existing.source_port_max = self.source_port_max
            existing.source_port_min = self.source_port_min
            existing.code = self.code
            existing.type = self.type
            existing.resource_id = self.resource_id
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.ACTION_KEY: self.action,
            self.DIRECTION_KEY: self.direction,
            self.DESTINATION_KEY: self.destination,
            self.SOURCE_KEY: self.source,
            self.PROTOCOL_KEY: self.protocol,
            self.DESTINATION_PORT_MAX_KEY: self.port_max,
            self.DESTINATION_PORT_MIN_KEY: self.port_min,
            self.SOURCE_PORT_MIN_KEY: self.source_port_min,
            self.SOURCE_PORT_MAX_KEY: self.source_port_max,
            self.CODE_KEY: self.code,
            self.TYPE_KEY: self.type,
        }

    def to_json_body(self):
        json_data = {
            "name": self.name,
            "action": self.action,
            "direction": self.direction,
            "protocol": self.protocol,
            "source": self.source or "0.0.0.0/0",
            "destination": self.destination or "0.0.0.0/0",
        }

        if self.protocol in ["tcp", "udp"]:
            json_data["destination_port_max"] = self.port_max
            json_data["destination_port_min"] = self.port_min
            json_data["source_port_max"] = self.source_port_max
            json_data["source_port_min"] = self.source_port_min

        elif self.protocol == "icmp":
            json_data["code"] = self.code
            json_data["type"] = self.type

        return json_data

    @classmethod
    def from_ibm_json_body(cls, json_body):
        # TODO: Check schema. Investigate resource_id = None for rules
        return IBMNetworkAclRule(
            name=json_body["name"],
            action=json_body["action"],
            destination=json_body["destination"],
            direction=json_body["direction"],
            source=json_body["source"],
            protocol=json_body.get("protocol", "all"),
            port_max=json_body.get("destination_port_max"),
            port_min=json_body.get("destination_port_min"),
            source_port_max=json_body.get("source_port_max"),
            source_port_min=json_body.get("source_port_min"),
            code=json_body.get("code"),
            type_=json_body.get("type"),
            status="CREATED"
        )
