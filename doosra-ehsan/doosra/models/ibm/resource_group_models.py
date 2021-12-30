import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import CREATED, PENDING, SUCCESS


class IBMResourceGroup(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    RESOURCE_ID_KEY = "resource_id"
    MESSAGE_KEY = ""
    STATUS_KEY = "status"
    RESOURCE_GROUP_KEY = "resource_group"

    __tablename__ = "ibm_resource_groups"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)

    vpc_networks = relationship(
        "IBMVpcNetwork",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    ike_policies = relationship(
        "IBMIKEPolicy",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    ipsec_policies = relationship(
        "IBMIPSecPolicy",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    public_gateways = relationship(
        "IBMPublicGateway",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    vpn_gateways = relationship(
        "IBMVpnGateway",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    security_groups = relationship(
        "IBMSecurityGroup",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    instances = relationship(
        "IBMInstance",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    ssh_keys = relationship(
        "IBMSshKey",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    load_balancers = relationship(
        "IBMLoadBalancer",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    images = relationship(
        "IBMImage",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    transit_gateways = relationship(
        "TransitGateway",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    kubernetes_clusters = relationship(
        "KubernetesCluster",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    dedicated_hosts = relationship(
        "IBMDedicatedHost",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    dedicated_host_groups = relationship(
        "IBMDedicatedHostGroup",
        backref="ibm_resource_group",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(name, cloud_id, name="uix_ibm_resource_group_name_cloud_id"),
    )

    def __init__(self, name, resource_id=None, cloud_id=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.resource_id = resource_id
        self.cloud_id = cloud_id

    def make_copy(self):
        return IBMResourceGroup(self.name, self.resource_id, self.cloud_id)

    def get_existing_from_db(self):
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, cloud_id=self.cloud_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not ((self.name == other.name) and (self.resource_id == other.resource_id)):
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
            existing.resource_id = self.resource_id
            db.session.commit()

        return existing

    def to_json(self):
        return {self.ID_KEY: self.id, self.NAME_KEY: self.name}

    def to_report_json(self, status):
        return {
            self.RESOURCE_GROUP_KEY: {
                self.ID_KEY: self.id,
                self.NAME_KEY: self.name,
                self.STATUS_KEY: SUCCESS if status == CREATED else PENDING,
                self.MESSAGE_KEY: ""
            }
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        ibm_resource_group = IBMResourceGroup(
            name=json_body["name"],
            resource_id=json_body["id"],
        )
        return ibm_resource_group
