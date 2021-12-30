import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import CREATION_PENDING, PENDING
from doosra.models.common_models import JSONEncodedDict, MutableDict

ibm_load_balancer_subnets = db.Table(
    "ibm_load_balancer_subnets",
    Column(
        "load_balancer_id",
        String(32),
        ForeignKey("ibm_load_balancers.id"),
        nullable=False,
    ),
    Column("subnets_id", String(32), ForeignKey("ibm_subnets.id"), nullable=False),
    PrimaryKeyConstraint("load_balancer_id", "subnets_id"),
)


class IBMLoadBalancer(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    PUBLIC_KEY = "is_public"
    RESOURCE_ID = "resource_id"
    STATUS_KEY = "status"
    PROVISIONING_STATUS_KEY = "provisioning_status"
    REGION_KEY = "region"
    PRIVATE_IPS_KEY = "private_ips"
    PUBLIC_IPS_KEY = "public_ips"
    HOST_NAME_KEY = "host_name"
    LISTENERS_KEY = "listeners"
    POOLS_KEY = "pools"
    SUBNETS_KEY = "subnets"
    RESOURCE_GROUP_KEY = "resource_group"
    VPC_KEY = "vpc"
    CLOUD_ID_KEY = "cloud_id"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_load_balancers"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    is_public = Column(Boolean, nullable=False)
    region = Column(String(32), nullable=False)
    resource_id = Column(String(64))
    host_name = Column(String(64))
    status = Column(String(50), nullable=False)
    private_ips = Column(MutableDict.as_mutable(JSONEncodedDict))
    public_ips = Column(MutableDict.as_mutable(JSONEncodedDict))
    provisioning_status = Column(String(50), nullable=True)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)
    # Temp column
    base_task_id = Column(String(100), nullable=True)
    listeners = relationship(
        "IBMListener",
        backref="ibm_load_balancer",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    pools = relationship(
        "IBMPool",
        backref="ibm_load_balancer",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    subnets = relationship(
        "IBMSubnet",
        secondary=ibm_load_balancer_subnets,
        backref=backref("ibm_load_balancers"),
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(name, vpc_id, cloud_id, region,
                         name="uix_ibm_lb_name_vpc_cloud_id_region"),
    )

    def __init__(
        self,
        name,
        is_public,
        region,
        vpc_id=None,
        host_name=None,
        status=None,
        resource_id=None,
        cloud_id=None,
        provisioning_status=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.is_public = is_public
        self.host_name = host_name
        self.status = status or CREATION_PENDING
        self.resource_id = resource_id
        self.region = region
        self.cloud_id = cloud_id
        self.vpc_id = vpc_id
        self.provisioning_status = provisioning_status

    def make_copy(self):
        obj = IBMLoadBalancer(
            name=self.name,
            is_public=self.is_public,
            region=self.region,
            host_name=self.host_name,
            status=self.status,
            resource_id=self.resource_id,
            cloud_id=self.cloud_id,
            provisioning_status=self.provisioning_status,
        )
        for listener in self.listeners.all():
            obj.listeners.append(listener.make_copy())

        for pool in self.pools.all():
            obj.pools.append(pool.make_copy())

        for subnet in self.subnets.all():
            obj.subnets.append(subnet.make_copy())

        if self.ibm_resource_group:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()

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
            and (self.region == other.region)
            and (self.is_public == other.is_public)
            and (self.resource_id == other.resource_id)
            and (self.status == other.status)
            and (self.provisioning_status == other.provisioning_status)
        ):
            return False

        if not len(self.listeners.all()) == len(other.listeners.all()):
            return False

        if not len(self.subnets.all()) == len(other.subnets.all()):
            return False

        if not len(self.pools.all()) == len(other.pools.all()):
            return False

        for listener in self.listeners.all():
            found = False
            for listener_ in other.listeners.all():
                if listener.params_eq(listener_):
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

        for pool in self.pools.all():
            found = False
            for pool_ in other.pools.all():
                if pool.params_eq(pool_):
                    found = True

            if not found:
                return False

        if self.private_ips and other.private_ips:
            if (
                self.private_ips.get("private_ips")
                and not other.private_ips.get("private_ips")
            ) or (
                not self.private_ips.get("private_ips")
                and other.private_ips.get("private_ips")
            ):
                return False

            if self.private_ips.get("private_ips") and other.private_ips.get(
                "private_ips"
            ):
                if not set(self.private_ips.get("private_ips")) == set(
                    self.private_ips.get("private_ips")
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

    def add_update_db(self, vpc):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            ibm_resource_group = self.ibm_resource_group
            subnets, listeners, pools = (
                self.subnets.all(),
                self.listeners.all(),
                self.pools.all(),
            )
            self.subnets, self.listeners, self.pools = list(), list(), list()
            self.ibm_resource_group = None
            self.ibm_vpc_network = vpc
            db.session.add(self)
            db.session.commit()

            for subnet in subnets:
                self.subnets.append(subnet.add_update_db(vpc))

            for listener in listeners:
                listener.add_update_db(self)

            for pool in pools:
                pool.add_update_db(self)

            if ibm_resource_group:
                self.ibm_resource_group = ibm_resource_group.add_update_db()
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.region = self.region
            existing.status = self.status
            existing.provisioning_status = self.provisioning_status
            existing.is_public = self.is_public
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

            for listener in existing.listeners.all():
                found = False
                for listener_ in self.listeners.all():
                    if listener.port == listener_.port:
                        found = True
                        break

                if not found:
                    existing.listeners.remove(listener)
                    db.session.commit()

            for pool in existing.pools.all():
                found = False
                for pool_ in self.pools.all():
                    if pool.name == pool_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(pool)
                    db.session.commit()

            subnets, listeners, pools = (
                self.subnets.all(),
                self.listeners.all(),
                self.pools.all(),
            )
            self.subnets, self.listeners, self.pools = list(), list(), list()
            ibm_resource_group = self.ibm_resource_group
            self.ibm_resource_group = None

            for subnet in subnets:
                subnet.add_update_db(vpc)
                db.session.commit()

            for listener in listeners:
                listener.add_update_db(existing)
                db.session.commit()

            for pool in pools:
                pool.add_update_db(existing)
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
            self.PUBLIC_KEY: self.is_public,
            self.REGION_KEY: self.region,
            self.STATUS_KEY: self.status,
            self.PROVISIONING_STATUS_KEY: self.provisioning_status,
            self.HOST_NAME_KEY: self.host_name,
            self.PRIVATE_IPS_KEY: self.private_ips.get("private_ips")
            if self.private_ips
            else "",
            self.PUBLIC_IPS_KEY: self.public_ips.get("public_ips")
            if self.public_ips
            else "",
            self.RESOURCE_GROUP_KEY: self.ibm_resource_group.to_json()
            if self.ibm_resource_group
            else {},
            self.CLOUD_ID_KEY: self.cloud_id,
            self.VPC_KEY: {
                self.ID_KEY: self.ibm_vpc_network.id,
                self.NAME_KEY: self.ibm_vpc_network.name,
            }
            if self.ibm_vpc_network
            else None,
            self.LISTENERS_KEY: [
                listener.to_json() for listener in self.listeners.all()
            ],
            self.SUBNETS_KEY: [subnet.to_json() for subnet in self.subnets.all()],
            self.POOLS_KEY: [pool.to_json() for pool in self.pools.all()],
        }

    def to_json_body(self):
        return {
            "resource_group": {
                "id": self.ibm_resource_group.resource_id
                if self.ibm_resource_group
                else ""
            },
            "name": self.name,
            "is_public": self.is_public,
            "subnets": [{"id": subnet.resource_id} for subnet in self.subnets.all()],
            "listeners": [listener.to_json_body() for listener in self.listeners.all()],
            "pools": [pool.to_json_body() for pool in self.pools.all()],
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
        if json_body["provisioning_status"] == "create_pending":
            status = "CREATING"
        elif json_body["provisioning_status"] == "active":
            status = "CREATED"
        elif json_body["provisioning_status"] == "update_pending":
            status = "UPDATING"
        elif json_body["provisioning_status"] == "delete_pending":
            status = "DELETING"
        elif json_body["provisioning_status"] == "failed":
            status = "ERROR_"

        assert status

        ibm_load_balancer = IBMLoadBalancer(
            name=json_body["name"], is_public=json_body["is_public"], region=region, host_name=json_body["hostname"],
            resource_id=json_body["id"], provisioning_status=json_body["provisioning_status"], status=status
        )

        public_ips_list = list()
        for ip in json_body["public_ips"]:
            public_ips_list.append(ip["address"])

        ibm_load_balancer.public_ips = {"public_ips": public_ips_list}

        private_ips_list = list()
        for ip in json_body["private_ips"]:
            private_ips_list.append(ip["address"])

        ibm_load_balancer.private_ips = {"private_ips": private_ips_list}

        return ibm_load_balancer


class IBMListener(db.Model):
    ID_KEY = "id"
    RESOURCE_ID = "resource_id"
    PORT_KEY = "port"
    PROTOCOL_KEY = "protocol"
    CERTIFICATE_INSTANCE = "crn"
    CONNECTION_LIMIT = "limit"
    STATUS_KEY = "status"
    DEFAULT_POOL_KEY = "default_pool_id"

    __tablename__ = "ibm_listeners"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    port = Column(Integer, nullable=False)
    protocol = Column(String(8), Enum("http", "https", "tcp"), nullable=False)
    crn = Column(String(255))
    limit = Column(Integer, default=2000)
    status = Column(String(50), nullable=False)

    load_balancer_id = Column(
        String(32), ForeignKey("ibm_load_balancers.id"), nullable=False
    )
    pool_id = Column(String(32), ForeignKey("ibm_pools.id"))

    def __init__(
        self,
        port,
        protocol,
        limit,
        crn=None,
        resource_id=None,
        status=None,
        pool_id=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.resource_id = resource_id
        self.port = port
        self.protocol = protocol
        self.crn = crn
        self.limit = limit
        self.status = status or CREATION_PENDING
        self.pool_id = pool_id

    def make_copy(self):
        obj = IBMListener(
            self.port,
            self.protocol,
            self.limit,
            self.crn,
            self.resource_id,
            self.status,
            self.pool_id,
        )
        if self.ibm_pool:
            obj.ibm_pool = self.ibm_pool.make_copy()
        return obj

    def get_existing_from_db(self, load_balancer=None):
        if load_balancer:
            return (
                db.session.query(self.__class__)
                .filter_by(
                    port=self.port, load_balancer_id=load_balancer.id
                )
                .first()
            )
        return (
            db.session.query(self.__class__)
            .filter_by(
                port=self.port, load_balancer_id=self.load_balancer_id
            )
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.resource_id == other.resource_id)
            and (self.port == other.port)
            and (self.protocol == other.protocol)
            and (self.limit == other.limit)
            and (self.crn == other.crn)
            and (self.status == other.status)
        ):
            return False

        if (self.ibm_pool and not other.ibm_pool) or (
            not self.ibm_pool and other.ibm_pool
        ):
            return False

        if self.ibm_pool and other.ibm_pool:
            if not self.ibm_pool.params_eq(other.ibm_pool):
                return False

        return True

    def add_update_db(self, load_balancer):
        existing = self.get_existing_from_db(load_balancer)
        if not existing:
            ibm_pool = self.ibm_pool
            self.ibm_pool = None
            self.ibm_load_balancer = load_balancer
            db.session.add(self)
            db.session.commit()

            if ibm_pool:
                self.ibm_pool = ibm_pool.add_update_db(load_balancer)

            return self

        if not self.params_eq(existing):
            existing.resource_id = self.resource_id
            existing.status = self.status
            existing.protocol = self.protocol
            existing.limit = self.limit

            ibm_pool = self.ibm_pool
            self.ibm_pool = None

            if ibm_pool:
                existing.ibm_pool = ibm_pool.add_update_db(load_balancer)

            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.STATUS_KEY: self.status,
            self.PORT_KEY: self.port,
            self.PROTOCOL_KEY: self.protocol,
            self.CERTIFICATE_INSTANCE: self.crn,
            self.CONNECTION_LIMIT: self.limit,
            self.DEFAULT_POOL_KEY: self.ibm_pool.id if self.ibm_pool else "",
        }

    def to_json_body(self):
        return {
            "protocol": self.protocol,
            "port": self.port,
            "connection_limit": self.limit,
            "default_pool": {"name": self.ibm_pool.name if self.ibm_pool else ""},
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        return IBMListener(
            port=json_body["port"], protocol=json_body["protocol"], limit=json_body["connection_limit"],
            resource_id=json_body["id"],
        )


class IBMPool(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    RESOURCE_ID = "resource_id"
    ALGORITHM_KEY = "algorithm"
    PROTOCOL_KEY = "protocol"
    SESSION_PERSISTENCE_KEY = "session_persistence"
    STATUS_KEY = "status"
    HEALTH_CHECK_KEY = "health_check"
    POOL_MEMBER_KEY = "pool_members"

    __tablename__ = "ibm_pools"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    resource_id = Column(String(64))
    algorithm = Column(
        String(32),
        Enum("least_connections", "round_robin", "weighted_round_robin"),
        nullable=False,
    )
    protocol = Column(String(8), Enum("http", "tcp"), nullable=False)
    session_persistence = Column(String(32), Enum("source_ip"))
    status = Column(String(50), nullable=False)

    load_balancer_id = Column(String(32), ForeignKey("ibm_load_balancers.id"))

    health_check = relationship(
        "IBMHealthCheck",
        backref="ibm_pool",
        cascade="all, delete-orphan",
        uselist=False,
    )
    listeners = relationship(
        "IBMListener", backref="ibm_pool", cascade="all, delete-orphan", lazy="dynamic"
    )
    pool_members = relationship(
        "IBMPoolMember",
        backref="ibm_pool",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(
            name, load_balancer_id, name="uix_ibm_pool_name_load_balancer_id"
        ),
    )

    def __init__(
        self,
        name,
        algorithm,
        protocol,
        session_persistence=None,
        resource_id=None,
        status=None,
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.resource_id = resource_id
        self.algorithm = algorithm
        self.protocol = protocol
        self.session_persistence = session_persistence
        self.status = status or CREATION_PENDING

    def make_copy(self):
        obj = IBMPool(
            self.name,
            self.algorithm,
            self.protocol,
            self.session_persistence,
            self.resource_id,
            self.status,
        )
        for member in self.pool_members.all():
            obj.pool_members.append(member.make_copy())

        if self.health_check:
            obj.health_check = self.health_check.make_copy()

        return obj

    def get_existing_from_db(self, load_balancer=None):
        if load_balancer:
            return (
                db.session.query(self.__class__)
                .filter_by(name=self.name, load_balancer_id=load_balancer.id)
                .first()
            )
        return (
            db.session.query(self.__class__)
            .filter_by(name=self.name, load_balancer_id=self.load_balancer_id)
            .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.name == other.name)
            and (self.resource_id == other.resource_id)
            and (self.algorithm == other.algorithm)
            and (self.protocol == other.protocol)
            and (self.session_persistence == other.session_persistence)
            and (self.status == other.status)
        ):
            return False

        if not len(self.pool_members.all()) == len(other.pool_members.all()):
            return False

        for pool_mem in self.pool_members.all():
            found = False
            for pool_mem_ in other.pool_members.all():
                if pool_mem.params_eq(pool_mem_):
                    found = True

            if not found:
                return False

        if (self.health_check and not other.health_check) or (
            not self.health_check and other.health_check
        ):
            return False

        if self.health_check and other.health_check:
            if not self.health_check.params_eq(other.health_check):
                return False

        return True

    def add_update_db(self, load_balancer):
        existing = self.get_existing_from_db(load_balancer)
        if not existing:
            pool_members, health_check = self.pool_members.all(), self.health_check
            self.pool_members, health_check = list(), None
            self.ibm_load_balancer = load_balancer
            db.session.add(self)
            db.session.commit()

            for pool_member in pool_members:
                pool_member.add_update_db(self)
                db.session.commit()

            if health_check:
                self.health_check = health_check.add_update_db(self)
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.resource_id = self.resource_id
            existing.algorithm = self.algorithm
            existing.protocol = self.protocol
            existing.session_persistence = self.session_persistence
            db.session.commit()

            for pool_member in existing.pool_members.all():
                found = False
                for pool_member_ in self.pool_members.all():
                    if not pool_member.instance and not pool_member_.instance:
                        continue

                    if pool_member.instance.name == pool_member_.instance.name:
                        found = True
                        break

                if not found:
                    db.session.delete(pool_member)
                    db.session.commit()

            pool_members, health_check = self.pool_members.all(), self.health_check
            self.pool_members, self.health_check = list(), None

            for pool_member in pool_members:
                pool_member.add_update_db(existing)
                db.session.commit()

            if health_check:
                existing.health_check = health_check.add_update_db(existing)
            else:
                existing.health_check = None

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.STATUS_KEY: self.status,
            self.NAME_KEY: self.name,
            self.PROTOCOL_KEY: self.protocol,
            self.SESSION_PERSISTENCE_KEY: self.session_persistence,
            self.ALGORITHM_KEY: self.algorithm,
            self.HEALTH_CHECK_KEY: self.health_check.to_json()
            if self.health_check
            else None,
            self.POOL_MEMBER_KEY: [
                pool_mem.to_json() for pool_mem in self.pool_members.all()
            ],
        }

    def to_json_body(self):
        json_data = {
            "name": self.name,
            "protocol": self.protocol,
            "algorithm": self.algorithm,
            "health_monitor": self.health_check.to_json_body()
            if self.health_check
            else "",
            "members": [
                pool_mem.to_json_body() for pool_mem in self.pool_members.all()
            ],
        }

        if self.session_persistence:
            json_data["session_persistence"] = {"type": self.session_persistence}

        return json_data


class IBMPoolMember(db.Model):
    ID_KEY = "id"
    PORT_KEY = "port"
    INSTANCE_KEY = "instance"
    INSTANCE_ID_KEY = "instance_id"

    __tablename__ = "ibm_pool_members"

    id = Column(String(32), primary_key=True)
    port = Column(Integer, nullable=False)
    weight = Column(Integer, default=0)
    resource_id = Column(String(64))
    status = Column(String(50), nullable=False)

    pool_id = Column(String(32), ForeignKey("ibm_pools.id"), nullable=False)
    instance_id = Column(String(32), ForeignKey("ibm_instances.id"))

    def __init__(self, port, weight=100, resource_id=None, status=None):
        self.id = str(uuid.uuid4().hex)
        self.port = port
        self.weight = weight
        self.resource_id = resource_id
        self.status = status or CREATION_PENDING

    def make_copy(self):
        obj = IBMPoolMember(self.port, self.weight, self.resource_id, status=self.status)
        if self.instance:
            obj.instance = self.instance.make_copy()

        return obj

    def get_existing_from_db(self, pool=None):
        if pool:
            pool_mems = db.session.query(self.__class__).filter_by(port=self.port, pool_id=pool.id).all()
        else:
            pool_mems = db.session.query(self.__class__).filter_by(port=self.port, pool_id=self.pool_id).all()

        for pool_mem in pool_mems:
            if pool_mem.instance and self.instance:
                if pool_mem.instance.name == self.instance.name:
                    return pool_mem

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not ((self.port == other.port) and (self.weight == other.weight) and
                (self.status == other.status) and (self.resource_id == other.resource_id)):
            return False

        if (self.instance and not other.instance) or (not self.instance and other.instance):
            return False

        if self.instance and other.instance:
            if not self.instance.params_eq(other.instance):
                return False

        return True

    def add_update_db(self, pool):
        existing = self.get_existing_from_db(pool)
        if not existing:
            instance = self.instance
            self.instance = None
            self.ibm_pool = pool
            db.session.add(self)
            db.session.commit()

            if instance:
                self.instance = instance.add_update_db(pool.ibm_load_balancer.ibm_vpc_network)
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.weight = self.weight
            existing.port = self.port
            existing.resource_id = self.resource_id
            existing.status = self.status
            db.session.commit()

            instance = self.instance
            self.instance = None

            if instance:
                existing.instance = instance.add_update_db(
                    pool.ibm_load_balancer.ibm_vpc_network
                )
            else:
                existing.instance = None

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.PORT_KEY: self.port,
            self.INSTANCE_KEY: self.instance.to_json() if self.instance else "",
        }

    def to_json_body(self):
        return {
            "target": {
                "address": [
                    interface.private_ip
                    for interface in self.instance.network_interfaces.all()
                    if interface.is_primary
                ][0]
                if self.instance
                else ""
            },
            "port": self.port,
            "weight": self.weight,
        }


class IBMHealthCheck(db.Model):
    ID_KEY = "id"
    DELAY_KEY = "delay"
    MAX_RETRIES_KEY = "max_retries"
    TIMEOUT_KEY = "timeout"
    TYPE_KEY = "type"
    PORT_KEY = "port"
    URL_KEY = "url_path"

    __tablename__ = "ibm_health_checks"

    id = Column(String(32), primary_key=True)
    delay = Column(Integer, nullable=False)
    max_retries = Column(Integer, nullable=False)
    timeout = Column(Integer, nullable=False)
    type = Column(String(8), Enum("http", "tcp"), nullable=False)
    port = Column(Integer, nullable=True)
    url_path = Column(String(255), default="/")

    pool_id = Column(String(32), ForeignKey("ibm_pools.id"), nullable=False)

    def __init__(
        self, delay, max_retries, timeout, type_, url_path, port=None, pool_id=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.delay = delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.type = type_
        self.port = port
        self.url_path = url_path
        self.pool_id = pool_id

    def make_copy(self):
        return IBMHealthCheck(
            self.delay,
            self.max_retries,
            self.timeout,
            self.type,
            self.url_path,
            self.port,
            self.pool_id,
        )

    def get_existing_from_db(self, pool=None):
        if pool:
            return db.session.query(self.__class__).filter_by(pool_id=pool.id).first()
        return db.session.query(self.__class__).filter_by(pool_id=self.pool_id).first()

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
            (self.delay == other.delay)
            and (self.max_retries == other.max_retries)
            and (self.timeout == other.timeout)
            and (self.type == other.type)
            and (self.port == other.port)
            and (self.url_path == other.url_path)
        ):
            return False

        return True

    def add_update_db(self, pool):
        existing = self.get_existing_from_db(pool)
        if not existing:
            self.ibm_pool = pool
            db.session.add(self)
            db.session.commit()
            return self

        if not self.params_eq(existing):
            existing.delay = self.delay
            existing.max_retries = self.max_retries
            existing.timeout = self.timeout
            existing.type = self.type
            existing.port = self.port
            existing.url_path = self.url_path
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.DELAY_KEY: self.delay,
            self.MAX_RETRIES_KEY: self.max_retries,
            self.TIMEOUT_KEY: self.timeout,
            self.TYPE_KEY: self.type,
            self.PORT_KEY: self.port,
            self.URL_KEY: self.url_path,
        }

    def to_json_body(self):
        return {
            "type": self.type,
            "delay": self.delay,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "url_path": self.url_path,
            "port": self.port,
        }
