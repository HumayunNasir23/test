import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String, desc,
)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import (
    CREATION_PENDING,
    CREATED,
    ERROR_CREATING, PENDING, SUCCESS,
)
from doosra.models import IBMTask


class IBMVpcNetwork(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    MESSAGE_KEY = "message"
    STATUS_KEY = "status"
    REGION_KEY = "region"
    CRN_KEY = "crn"
    ADDRESS_MANAGEMENT_PREFIX_KEY = "address_prefix_management"
    CLASSIC_ACCESS_KEY = "classic_access"
    RESOURCE_GROUP_KEY = "resource_group"
    ACL_KEY = "acls"
    SECURITY_GROUPS_KEY = "security_groups"
    ADDRESS_PREFIX_KEY = "address_prefixes"
    SUBNET_KEY = "subnets"
    INSTANCES_KEY = "instances"
    CLOUD_ID_KEY = "cloud"
    LOAD_BALANCER_KEY = "load_balancers"
    VPN_GATEWAY_KEY = "vpn_gateways"
    PUBLIC_GATEWAY_KEY = "public_gateways"
    K8S_CLUSTER_KEY = "k8s_clusters"
    ROUTES_KEY = "routes"
    ACTION_KEY = "action"
    WORKSPACE_ID_KEY = "workspace_id"
    VPC_KEY = "vpc"
    REPORT_TASK_ID = "report_task_id"

    __tablename__ = "ibm_vpc_networks"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    crn = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    message = Column(String(300), nullable=True)
    region = Column(String(255), nullable=False)
    action = Column(String(50))
    address_prefix_management = Column(
        Enum("auto", "manual"), default="auto", nullable=False
    )
    classic_access = Column(Boolean, nullable=False, default=False)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))
    workspace_id = Column(String(32), ForeignKey("workspaces.id"))

    acls = relationship("IBMNetworkAcl", backref="ibm_vpc_network", cascade="all, delete-orphan", lazy="dynamic")

    vpc_routes = relationship(
        "IBMVpcRoute",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    subnets = relationship(
        "IBMSubnet",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    public_gateways = relationship(
        "IBMPublicGateway",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    security_groups = relationship(
        "IBMSecurityGroup",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    instances = relationship(
        "IBMInstance",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    load_balancers = relationship(
        "IBMLoadBalancer",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    vpn_gateways = relationship(
        "IBMVpnGateway",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    address_prefixes = relationship(
        "IBMAddressPrefix",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    transit_gateway_connection = relationship(
        "TransitGatewayConnection",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        uselist=False
    )
    kubernetes_clusters = relationship(
        "KubernetesCluster",
        backref="ibm_vpc_network",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint(name, cloud_id, region, name="uix_ibm_vpc_network_name_cloud_id_region"),
    )

    def __init__(
            self,
            name,
            region,
            classic_access=False,
            cloud_id=None,
            crn=None,
            resource_id=None,
            status=CREATION_PENDING,
            address_prefix_management=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = status
        self.region = region
        self.crn = crn,
        self.address_prefix_management = address_prefix_management or "auto"
        self.classic_access = classic_access
        self.cloud_id = cloud_id
        self.resource_id = resource_id

    def set_error_status(self):
        if not self.status == CREATED:
            self.status = ERROR_CREATING
            db.session.commit()

            for obj in self.subnets.all():
                obj.set_error_status()

            for obj in self.public_gateways.all():
                obj.set_error_status()

            for obj in self.instances.all():
                obj.set_error_status()

    def make_copy(self):
        obj = IBMVpcNetwork(
            name=self.name,
            region=self.region,
            classic_access=self.classic_access,
            cloud_id=self.cloud_id,
            resource_id=self.resource_id,
            status=self.status,
            crn=self.crn,
            address_prefix_management=self.address_prefix_management,
        )

        for security_group in self.security_groups.all():
            obj.security_groups.append(security_group.make_copy())

        for subnet in self.subnets.all():
            obj.subnets.append(subnet.make_copy())

        for address_prefix in self.address_prefixes.all():
            obj.address_prefixes.append(address_prefix.make_copy())

        for public_gateway in self.public_gateways.all():
            obj.public_gateways.append(public_gateway.make_copy())

        for instance in self.instances.all():
            obj.instances.append(instance.make_copy())

        for load_balancer in self.load_balancers.all():
            obj.load_balancers.append(load_balancer.make_copy())

        for vpn_gateway in self.vpn_gateways.all():
            obj.vpn_gateways.append(vpn_gateway.make_copy())

        for route in self.vpc_routes.all():
            obj.vpc_routes.append(route.make_copy())

        for acl in self.acls.all():
            obj.acls.append(acl.make_copy())

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
                and (self.status == other.status)
                and (self.classic_access == other.classic_access)
                and (self.resource_id == other.resource_id)
        ):
            return False

        if not len(self.security_groups.all()) == len(other.security_groups.all()):
            return False

        if not len(self.public_gateways.all()) == len(other.public_gateways.all()):
            return False

        if not len(self.subnets.all()) == len(other.subnets.all()):
            return False

        if not len(self.instances.all()) == len(other.instances.all()):
            return False

        if not len(self.load_balancers.all()) == len(other.load_balancers.all()):
            return False

        if not len(self.vpn_gateways.all()) == len(other.vpn_gateways.all()):
            return False

        if not len(self.vpc_routes.all()) == len(other.vpc_routes.all()):
            return False

        if not len(self.acls.all()) == len(other.acls.all()):
            return False

        for instance in self.instances.all():
            found = False
            for instance_ in other.instances.all():
                if instance.params_eq(instance_):
                    found = True

            if not found:
                return False

        for subnet in self.subnets.all():
            found = False
            for subnet_ in other.subnets.all():
                if subnet.params_eq(subnet_):
                    found = True

            if not found:
                return False

        for security_group in self.security_groups.all():
            found = False
            for security_group_ in other.security_groups.all():
                if security_group.params_eq(security_group_):
                    found = True

            if not found:
                return False

        for public_gateway in self.public_gateways.all():
            found = False
            for public_gateway_ in other.public_gateways.all():
                if public_gateway.params_eq(public_gateway_):
                    found = True

            if not found:
                return False

        for load_balancer in self.load_balancers.all():
            found = False
            for load_balancer_ in other.load_balancers.all():
                if load_balancer.params_eq(load_balancer_):
                    found = True

            if not found:
                return False

        for vpn_gateway in self.vpn_gateways.all():
            found = False
            for vpn_gateway_ in other.vpn_gateways.all():
                if vpn_gateway.params_eq(vpn_gateway_):
                    found = True

            if not found:
                return False

        for route in self.vpc_routes.all():
            found = False
            for route_ in other.vpc_routes.all():
                if route.params_eq(route_):
                    found = True

            if not found:
                return False

        for acl in self.acls.all():
            found = False
            for acl_ in other.acls.all():
                if acl.params_eq(acl_):
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

    def add_update_db(self):
        existing = self.get_existing_from_db()
        if not existing:
            (
                subnets,
                public_gateways,
                instances,
                load_balancers,
                vpn_gateways,
                vpc_routes,
                acls,
            ) = (
                self.subnets.all(),
                self.public_gateways.all(),
                self.instances.all(),
                self.load_balancers.all(),
                self.vpn_gateways.all(),
                self.vpc_routes.all(),
                self.acls.all(),
            )
            security_groups, address_prefixes = (
                self.security_groups.all(),
                self.address_prefixes.all(),
            )
            ibm_resource_group = (
                self.ibm_resource_group,
            )

            (
                self.public_gateways,
                self.subnets,
                self.instances,
                self.address_prefixes,
            ) = (
                list(),
                list(),
                list(),
                list(),
            )

            (
                self.load_balancers,
                self.vpn_gateways,
                self.vpc_routes,
                self.security_groups,
                self.acls
            ) = (
                list(),
                list(),
                list(),
                list(),
                list()
            )
            self.ibm_resource_group = None
            db.session.add(self)
            db.session.commit()

            for subnet in subnets:
                subnet.add_update_db(self)
                db.session.commit()

            for instance in instances:
                instance.add_update_db(self)
                db.session.commit()

            for public_gateway in public_gateways:
                public_gateway.add_update_db(self)
                db.session.commit()

            for load_balancer in load_balancers:
                load_balancer.add_update_db(self)
                db.session.commit()

            for vpn_gateway in vpn_gateways:
                vpn_gateway.add_update_db(self)
                db.session.commit()

            for route in vpc_routes:
                route.add_update_db(self)
                db.session.commit()

            for security_group in security_groups:
                security_group.add_update_db(self)
                db.session.commit()

            for address_prefix in address_prefixes:
                address_prefix.add_update_db(self)
                db.session.commit()

            for acl in acls:
                acl.add_update_db(self)
                db.session.commit()

            if ibm_resource_group:
                self.ibm_resource_group = ibm_resource_group.make_copy().add_update_db()
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.region = self.region
            existing.status = self.status
            existing.crn = self.crn
            existing.classic_access = self.classic_access
            existing.resource_id = self.resource_id
            db.session.commit()

            for subnet in existing.subnets.all():
                found = False
                for subnet_ in self.subnets.all():
                    if subnet.name == subnet_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(subnet)
                    db.session.commit()

            for acl in existing.acls.all():
                found = False
                for acl_ in self.acls.all():
                    if acl.name == acl_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(acl)
                    db.session.commit()

            for public_gateway in existing.public_gateways.all():
                found = False
                for public_gateway_ in self.public_gateways.all():
                    if public_gateway.name == public_gateway_.name:
                        found = True
                        break

                if not found:
                    existing.public_gateways.remove(public_gateway)
                    db.session.commit()

            for security_group in existing.security_groups.all():
                found = False
                for security_group_ in self.security_groups.all():
                    if security_group.name == security_group_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(security_group)
                    db.session.commit()

            for instance in existing.instances.all():
                found = False
                for instance_ in self.instances.all():
                    if instance.name == instance_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(instance)
                    db.session.commit()

            for load_balancer in existing.load_balancers.all():
                found = False
                for load_balancer_ in self.load_balancers.all():
                    if load_balancer.name == load_balancer_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(load_balancer)
                    db.session.commit()

            for vpn_gateway in existing.vpn_gateways.all():
                found = False
                for vpn_gateway_ in self.vpn_gateways.all():
                    if vpn_gateway.name == vpn_gateway_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(vpn_gateway)
                    db.session.commit()

            for route in existing.vpc_routes.all():
                found = False
                for route_ in self.vpc_routes.all():
                    if route.name == route_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(route)
                    db.session.commit()

            for address_prefix in existing.address_prefixes.all():
                found = False
                for address_prefix_ in self.address_prefixes.all():
                    if (
                            address_prefix.address == address_prefix_.address
                            and address_prefix.zone == address_prefix_.zone
                    ):
                        found = True
                        break

                if not found:
                    db.session.delete(address_prefix)
                    db.session.commit()

            public_gateways, address_prefixes = (
                self.public_gateways.all(),
                self.address_prefixes.all(),
            )
            instances, load_balancers, subnets = (
                self.instances.all(),
                self.load_balancers.all(),
                self.subnets.all(),
            )
            vpn_gateways, vpc_routes, security_groups, acls = (
                self.vpn_gateways.all(),
                self.vpc_routes.all(),
                self.security_groups.all(),
                self.acls.all(),
            )
            ibm_resource_group, = (
                self.ibm_resource_group,
            )
            self.instances, self.load_balancers, self.vpn_gateways, self.vpc_routes = (
                list(),
                list(),
                list(),
                list(),
            )
            self.address_prefixes, self.acls = list(), list()
            self.public_gateways, self.subnets, self.security_groups = (
                list(),
                list(),
                list(),
            )
            self.ibm_resource_group = None

            for security_group in security_groups:
                security_group.add_update_db(existing)
                db.session.commit()

            for subnet in subnets:
                subnet.add_update_db(existing)
                db.session.commit()

            for public_gateway in public_gateways:
                public_gateway.add_update_db(existing)
                db.session.commit()

            for instance in instances:
                instance.add_update_db(existing)
                db.session.commit()

            for load_balancer in load_balancers:
                load_balancer.add_update_db(existing)
                db.session.commit()

            for vpn_gateway in vpn_gateways:
                vpn_gateway.add_update_db(existing)
                db.session.commit()

            for vpc_route in vpc_routes:
                vpc_route.add_update_db(existing)
                db.session.commit()

            for address_prefix in address_prefixes:
                address_prefix.add_update_db(existing)
                db.session.commit()

            for acl in acls:
                acl.add_update_db(existing)
                db.session.commit()

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
            self.CLOUD_ID_KEY: self.cloud_id,
            self.STATUS_KEY: self.status,
            self.ACTION_KEY: self.action,
            self.MESSAGE_KEY: self.message,
            self.REGION_KEY: self.region,
            self.ADDRESS_MANAGEMENT_PREFIX_KEY: self.address_prefix_management,
            self.CLASSIC_ACCESS_KEY: self.classic_access,
            self.WORKSPACE_ID_KEY: self.workspace_id or "",
            self.RESOURCE_GROUP_KEY: self.ibm_resource_group.to_json()
            if self.ibm_resource_group
            else {},
            self.SUBNET_KEY: [subnet.to_json() for subnet in self.subnets.all()],
            self.ACL_KEY: [acl.to_json() for acl in self.acls.all()],
            self.SECURITY_GROUPS_KEY: [
                security_group.to_json()
                for security_group in self.security_groups.all()
            ],
            self.INSTANCES_KEY: [
                instance.to_json() for instance in self.instances.all()
            ],
            self.LOAD_BALANCER_KEY: [
                load_balancer.to_json() for load_balancer in self.load_balancers.all()
            ],
            self.VPN_GATEWAY_KEY: [
                vpn_gateway.to_json() for vpn_gateway in self.vpn_gateways.all()
            ],
            self.ADDRESS_PREFIX_KEY: [
                address_prefix.to_json()
                for address_prefix in self.address_prefixes.all()
            ],
            self.PUBLIC_GATEWAY_KEY: [
                public_gateway.to_json()
                for public_gateway in self.public_gateways.all()
            ],
            self.K8S_CLUSTER_KEY: [
                kubernetes_cluster.to_json()
                for kubernetes_cluster in self.kubernetes_clusters.all()
            ],
            self.ROUTES_KEY: [route.to_json() for route in self.vpc_routes.all()],
            self.CRN_KEY: self.crn,
            self.REPORT_TASK_ID: self.get_resource_task_id()
        }

        return json_data

    def to_json_body(self):
        return {
            "name": self.name,
            "classic_access": self.classic_access,
            "resource_group": {"id": self.ibm_resource_group.resource_id},
            "address_prefix_management": self.address_prefix_management,
        }

    def to_report_json(self):
        return {
            self.VPC_KEY: {
                self.ID_KEY: self.id,
                self.NAME_KEY: self.name,
                self.STATUS_KEY: SUCCESS if self.status == CREATED else PENDING,
                self.MESSAGE_KEY: ""
            }
        }

    def get_resource_task_id(self):
        """
        This method return resource task id.
        :return:
        """
        task = db.session.query(IBMTask).filter(
            IBMTask.resource_id == self.id, IBMTask.report.isnot(None)).order_by(desc(IBMTask.started_at)).first()

        return task.id if task else None

    @classmethod
    def from_ibm_json_body(cls, region, json_body):
        status = None
        if json_body["status"] == "pending":
            status = "PENDING"
        elif json_body["status"] == "available":
            status = "CREATED"
        elif json_body["status"] == "deleting":
            status = "DELETING"
        elif json_body["status"] == "failed":
            status = "ERROR_"

        assert status

        ibm_vpc_network = IBMVpcNetwork(
            name=json_body["name"],
            region=region,
            classic_access=json_body["classic_access"],
            crn=json_body["crn"],
            resource_id=json_body["id"],
            status=status
        )

        return ibm_vpc_network


class IBMVpcRoute(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    REGION_KEY = "region"
    RESOURCE_ID_KEY = "resource_id"
    DESTINATION_KEY = "destination"
    ZONE_KEY = "zone"
    CREATED_AT_KEY = "created_at"
    LIFE_CYCLE_STATE_KEY = "lifecycle_state"
    NEXT_HOP_KEY = "next_hop"
    MESSAGE_KEY = "message"
    VPC_KEY = "vpc"

    __tablename__ = "ibm_vpc_routes"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    region = Column(String(50), nullable=True)
    zone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow())
    lifecycle_state = Column(
        Enum(
            "deleted", "deleting", "failed", "pending", "stable", "updating", "waiting"
        ),
        default="pending",
    )
    destination = Column(String(32), nullable=True)
    next_hop_address = Column(String(16), nullable=True)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint(name, vpc_id, cloud_id, name="uix_ibm_route_name_cloud_id"),
    )

    def __init__(
            self,
            name,
            status=None,
            resource_id=None,
            region=None,
            zone=None,
            created_at=None,
            lifecycle_state=None,
            next_hop_address=None,
            destination=None,
            cloud_id=None,
            vpc_id=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = status or CREATION_PENDING
        self.resource_id = resource_id
        self.region = region
        self.zone = zone
        self.created_at = created_at
        self.lifecycle_state = lifecycle_state
        self.destination = destination
        self.next_hop_address = next_hop_address
        self.vpc_id = vpc_id
        self.cloud_id = cloud_id

    def make_copy(self):
        return IBMVpcRoute(
            self.name,
            self.status,
            self.resource_id,
            self.region,
            self.zone,
            self.created_at,
            self.lifecycle_state,
            self.destination,
            self.next_hop_address,
            cloud_id=self.cloud_id
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
                and (self.resource_id == other.resource_id)
                and (self.zone == other.zone)
                and (self.region == other.region)
                and (self.lifecycle_state == other.lifecycle_state)
                and (self.destination == other.destination)
                and (self.next_hop_address == other.next_hop_address)
                and (self.status == other.status)
        ):
            return False

        return True

    def add_update_db(self, vpc):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            db.session.add(self)
            db.session.commit()
            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.resource_id = self.resource_id
            existing.zone = self.zone
            existing.region = self.region
            existing.lifecycle_state = self.lifecycle_state
            existing.destination = self.destination
            existing.next_hop_address = self.next_hop_address
            existing.status = self.status
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.CREATED_AT_KEY: str(self.created_at),
            self.LIFE_CYCLE_STATE_KEY: self.lifecycle_state,
            self.DESTINATION_KEY: self.destination,
            self.NEXT_HOP_KEY: self.next_hop_address,
            self.STATUS_KEY: self.status,
            self.REGION_KEY: self.region,
            self.ZONE_KEY: self.zone,
            self.VPC_KEY: self.vpc_id,
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "destination": self.destination,
            "next_hop": {"address": self.next_hop_address},
            "zone": {"name": self.zone},
        }

    @classmethod
    def from_ibm_json_body(cls, region, json_body):
        status = None
        if json_body["lifecycle_state"] in ["pending", "waiting"]:
            status = "CREATING"
        elif json_body["lifecycle_state"] in ["stable", "updating"]:
            status = "CREATED"
        elif json_body["lifecycle_state"] == "deleting":
            status = "DELETING"
        elif json_body["lifecycle_state"] == "deleted":
            status = "DELETED"
        elif json_body["lifecycle_state"] == "failed":
            status = "ERROR_"

        assert status
        ibm_vpc_route = IBMVpcRoute(
            name=json_body["name"], resource_id=json_body["id"], region=region,
            zone=json_body["zone"]["name"], created_at=json_body["created_at"],
            lifecycle_state=json_body["lifecycle_state"], destination=json_body["destination"],
            next_hop_address=json_body["next_hop"]["address"], status=status
        )

        return ibm_vpc_route

    def to_report_json(self):
        json_data = {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }

        return json_data
