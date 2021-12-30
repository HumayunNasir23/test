"""
Models for Dedicated hosts
"""
import uuid

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, JSON, PrimaryKeyConstraint, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import CREATION_PENDING


ibm_dh_supported_instance_profiles = db.Table(
    "ibm_dh_supported_instance_profiles",
    Column("dh_id", String(32), ForeignKey("ibm_dedicated_hosts.id"), nullable=False),
    Column("instance_profile_id", String(32), ForeignKey("ibm_instance_profiles.id"), nullable=False),
    PrimaryKeyConstraint("dh_id", "instance_profile_id"),
)

ibm_dh_group_supported_instance_profiles = db.Table(
    "ibm_dh_group_supported_instance_profiles",
    Column("dh_group_id", String(32), ForeignKey("ibm_dedicated_host_groups.id"), nullable=False),
    Column("instance_profile_id", String(32), ForeignKey("ibm_instance_profiles.id"), nullable=False),
    PrimaryKeyConstraint("dh_group_id", "instance_profile_id"),
)

ibm_dh_profile_supported_instance_profiles = db.Table(
    "ibm_dh_profile_supported_instance_profiles",
    Column("dh_profile_id", String(32), ForeignKey("ibm_dedicated_host_profiles.id"), nullable=False),
    Column("instance_profile_id", String(32), ForeignKey("ibm_instance_profiles.id"), nullable=False),
    PrimaryKeyConstraint("dh_profile_id", "instance_profile_id"),
)


class IBMDedicatedHost(db.Model):
    """
    Model for Dedicated host
    """
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    REGION_KEY = "region"
    ZONE_KEY = "zone"
    RESOURCE_ID_KEY = "resource_id"
    CRN_KEY = "crn"
    HREF_KEY = "href"
    INSTANCE_PLACEMENT_ENABLED_KEY = "instance_placement_enabled"
    LIFECYCLE_STATE_KEY = "lifecycle_state"
    AVAILABLE_MEMORY_KEY = "available_memory"
    MEMORY_KEY = "memory"
    PROVISIONABLE_KEY = "provisionable"
    SOCKET_COUNT_KEY = "socket_count"
    STATE_KEY = "state"
    VCPU_KEY = "vcpu"
    AVAILABLE_VCPU_KEY = "available_vpcu"
    RESOURCE_GROUP_KEY = "resource_group"
    DEDICATED_HOST_GROUP_KEY = "dedicated_host_group"
    DEDICATED_HOST_PROFILE_KEY = "dedicated_host_profile"
    INSTANCES_KEY = "instances"
    DEDICATED_HOST_DISKS_KEY = "dedicated_host_disks"
    SUPPORTED_INSTANCE_PROFILES_KEY = "supported_instance_profiles"

    __tablename__ = "ibm_dedicated_hosts"
    # resource_type missing. Not needed I guess
    id = Column(String(32), primary_key=True)
    name = Column(String(255))
    status = Column(String(50), nullable=False)
    region = Column(String(128), nullable=False)
    zone = Column(String(20), nullable=False)
    resource_id = Column(String(64))
    crn = Column(Text)
    href = Column(Text)
    instance_placement_enabled = Column(Boolean, default=True)
    lifecycle_state = Column(
        Enum("deleting", "failed", "pending", "stable", "updating", "waiting", "suspended"),
        default="stable")
    available_memory = Column(Integer)
    memory = Column(Integer)
    provisionable = Column(Boolean)
    socket_count = Column(Integer)
    state = Column(Enum("available", "degraded", "migrating", "unavailable"))
    vcpu = Column(JSON)
    available_vcpu = Column(JSON)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))
    dedicated_host_group_id = Column(String(32), ForeignKey("ibm_dedicated_host_groups.id"))
    dedicated_host_profile_id = Column(String(32), ForeignKey("ibm_dedicated_host_profiles.id"), nullable=False)

    instances = relationship("IBMInstance", backref="ibm_dedicated_host", cascade="all, delete-orphan", lazy="dynamic")
    dedicated_host_disks = relationship(
        "IBMDedicatedHostDisk", backref="ibm_dedicated_host", cascade="all, delete-orphan", lazy="dynamic"
    )
    supported_instance_profiles = relationship(
        "IBMInstanceProfile", secondary=ibm_dh_supported_instance_profiles, backref="ibm_dedicated_hosts",
        lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint(
            name, region, cloud_id, name="uix_ibm_dh_name_region_cloudid"
        ),
    )

    def __init__(
            self, name=None, status=None, region=None, zone=None, resource_id=None, crn=None, href=None,
            instance_placement_enabled=True, lifecycle_state=None, available_memory=None, memory=None,
            provisionable=True, socket_count=None, state=None, vcpu=None, available_vcpu=None, cloud_id=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = status or CREATION_PENDING
        self.region = region
        self.zone = zone
        self.resource_id = resource_id
        self.crn = crn
        self.href = href
        self.instance_placement_enabled = instance_placement_enabled
        self.lifecycle_state = lifecycle_state
        self.available_memory = available_memory
        self.memory = memory
        self.provisionable = provisionable
        self.socket_count = socket_count
        self.state = state
        self.vcpu = vcpu
        self.available_vcpu = available_vcpu
        self.cloud_id = cloud_id

    def to_json(self):
        """
        Return a JSON representation of the object
        """
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.REGION_KEY: self.region,
            self.ZONE_KEY: self.zone,
            self.RESOURCE_ID_KEY: self.resource_id,
            self.CRN_KEY: self.crn,
            self.INSTANCE_PLACEMENT_ENABLED_KEY: self.instance_placement_enabled,
            self.LIFECYCLE_STATE_KEY: self.lifecycle_state,
            self.AVAILABLE_MEMORY_KEY: self.available_memory,
            self.MEMORY_KEY: self.memory,
            self.PROVISIONABLE_KEY: self.provisionable,
            self.SOCKET_COUNT_KEY: self.socket_count,
            self.STATE_KEY: self.state,
            self.VCPU_KEY: self.vcpu,
            self.AVAILABLE_VCPU_KEY: self.available_vcpu,
            self.RESOURCE_GROUP_KEY: {self.ID_KEY: self.resource_group_id} if self.resource_group_id else None,
            self.DEDICATED_HOST_GROUP_KEY:
                {
                    self.ID_KEY: self.dedicated_host_group_id, self.NAME_KEY: self.ibm_dedicated_host_group.name
                } if self.dedicated_host_group_id else None,
            self.DEDICATED_HOST_PROFILE_KEY:
                {
                    self.ID_KEY: self.dedicated_host_profile_id, self.NAME_KEY: self.ibm_dedicated_host_profile.name
                } if self.dedicated_host_profile_id else None,
            self.SUPPORTED_INSTANCE_PROFILES_KEY: [sip.to_json() for sip in self.supported_instance_profiles.all()],
            self.INSTANCES_KEY: [instance.id for instance in self.instances.all()]
        }

    def to_json_body(self):
        """
        Return a JSON representation of the object according to IBM's CREATE API Call
        """
        json_data = {
            "profile": {
                "name": self.ibm_dedicated_host_profile.name
            }
        }
        # DO NOT simplify the following expression
        if self.instance_placement_enabled is False:
            json_data["instance_placement_enabled"] = self.instance_placement_enabled,

        if self.name:
            json_data["name"] = self.name

        if self.ibm_resource_group:
            json_data["resource_group"] = {
                "id": self.ibm_resource_group.resource_id
            }

        if self.ibm_dedicated_host_group.resource_id:
            json_data["group"] = {
                "id": self.ibm_dedicated_host_group.resource_id
            }
        else:
            json_data["zone"] = {
                "name": self.zone
            }
            if self.ibm_dedicated_host_group.name:
                json_data["group"] = {
                    "name": self.ibm_dedicated_host_group.name
                }

            if self.ibm_dedicated_host_group.ibm_resource_group:
                json_data["group"] = json_data.get("group") or {}
                json_data["group"]["resource_group"] = {
                    "id": self.ibm_dedicated_host_group.ibm_resource_group.resource_id
                }

        return json_data

    def update_from_obj(self, updated_obj):
        self.name = updated_obj.name
        self.status = updated_obj.status
        self.region = updated_obj.region
        self.zone = updated_obj.zone
        self.resource_id = updated_obj.resource_id
        self.crn = updated_obj.crn
        self.href = updated_obj.href
        self.instance_placement_enabled = updated_obj.instance_placement_enabled
        self.lifecycle_state = updated_obj.lifecycle_state
        self.available_memory = updated_obj.available_memory
        self.memory = updated_obj.memory
        self.provisionable = updated_obj.provisionable
        self.socket_count = updated_obj.socket_count
        self.state = updated_obj.state
        self.vcpu = updated_obj.vcpu
        self.available_vcpu = updated_obj.available_vcpu

    @classmethod
    def from_ibm_json(cls, json_body):
        """
        Return an object of the class created from the provided JSON body
        """
        return cls(
            name=json_body["name"],
            status="CREATED",
            region=json_body["href"].split("//")[1].split(".")[0],
            zone=json_body["zone"]["name"],
            resource_id=json_body["id"],
            crn=json_body["crn"],
            href=json_body["href"],
            instance_placement_enabled=json_body["instance_placement_enabled"],
            lifecycle_state=json_body["lifecycle_state"],
            available_memory=json_body["available_memory"],
            memory=json_body["memory"],
            provisionable=json_body["provisionable"],
            socket_count=json_body["socket_count"],
            state=json_body["state"],
            vcpu=json_body["vcpu"],
            available_vcpu=json_body["available_vcpu"]
        )

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: "SUCCESS" if self.status == "CREATED" else "PENDING",
            "message": ""
        }


class IBMDedicatedHostGroup(db.Model):
    """
    Model for Dedicated host group
    """
    ID_KEY = "id"
    NAME_KEY = "name"
    REGION_KEY = "region"
    ZONE_KEY = "zone"
    STATUS_KEY = "status"
    RESOURCE_ID_KEY = "resource_id"
    CRN_KEY = "crn"
    HREF_KEY = "href"
    FAMILY_KEY = "family"
    CLASS_KEY = "class"
    RESOURCE_GROUP_KEY = "resource_group"
    DEDICATED_HOSTS_KEY = "dedicated_hosts"
    SUPPORTED_INSTANCE_PROFILES_KEY = "supported_instance_profiles"

    __tablename__ = "ibm_dedicated_host_groups"
    # resource_type missing. Not needed I guess?
    id = Column(String(32), primary_key=True)
    name = Column(String(255))
    region = Column(String(128), nullable=False)
    zone = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False)
    resource_id = Column(String(64))
    crn = Column(Text)
    href = Column(Text)
    family = Column(Enum("balanced", "memory", "compute"))
    class_ = Column("class", String(128))

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))

    dedicated_hosts = relationship(
        "IBMDedicatedHost", backref="ibm_dedicated_host_group", cascade="all, delete-orphan", lazy="dynamic"
    )
    supported_instance_profiles = relationship(
        "IBMInstanceProfile", secondary=ibm_dh_group_supported_instance_profiles, backref="ibm_dedicated_host_groups",
        lazy="dynamic"
    )
    instances = relationship(
        "IBMInstance", backref="ibm_dedicated_host_group", cascade="all, delete-orphan", lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint(
            name, region, cloud_id, name="uix_ibm_dh_group_name_region_cloudid"
        ),
    )

    def __init__(
            self, name, region=None, zone=None, status=None, resource_id=None, crn=None, href=None, family=None,
            class_=None, cloud_id=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.zone = zone
        self.status = status or CREATION_PENDING
        self.resource_id = resource_id
        self.crn = crn
        self.href = href
        self.family = family
        self.class_ = class_
        self.cloud_id = cloud_id

    def to_json(self):
        """
        Return a JSON representation of the object
        """
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.REGION_KEY: self.region,
            self.ZONE_KEY: self.zone,
            self.STATUS_KEY: self.status,
            self.RESOURCE_ID_KEY: self.resource_id,
            self.CRN_KEY: self.crn,
            self.FAMILY_KEY: self.family,
            self.CLASS_KEY: self.class_,
            self.RESOURCE_GROUP_KEY: {self.ID_KEY: self.resource_group_id},
            self.DEDICATED_HOSTS_KEY:
                [{self.ID_KEY: dedicated_host.id} for dedicated_host in self.dedicated_hosts.all()],
            self.SUPPORTED_INSTANCE_PROFILES_KEY: [sip.to_json() for sip in self.supported_instance_profiles.all()]

        }

    def to_json_body(self):
        """
        Return a JSON representation of the object according to IBM's CREATE API Call
        """
        json_data = {
            self.CLASS_KEY: self.class_,
            self.FAMILY_KEY: self.family,
            self.ZONE_KEY: {
                self.NAME_KEY: self.zone
            },
            self.NAME_KEY: self.name
        }
        if self.ibm_resource_group:
            json_data[self.RESOURCE_GROUP_KEY] = {
                self.ID_KEY: self.ibm_resource_group.resource_id
            }

        return json_data

    def update_from_obj(self, updated_obj):
        assert isinstance(updated_obj, IBMDedicatedHostGroup)
        self.name = updated_obj.name
        self.region = updated_obj.region
        self.zone = updated_obj.zone
        self.status = updated_obj.status
        self.resource_id = updated_obj.resource_id
        self.crn = updated_obj.crn
        self.href = updated_obj.href
        self.family = updated_obj.family
        self.class_ = updated_obj.class_

    @classmethod
    def from_ibm_json(cls, json_body):
        """
        Return an object of the class created from the provided JSON body
        """
        return cls(
            name=json_body["name"],
            region=json_body["href"].split("//")[1].split(".")[0],
            zone=json_body["zone"]["name"],
            status="CREATED",
            resource_id=json_body["id"],
            crn=json_body["crn"],
            href=json_body["href"],
            family=json_body["family"],
            class_=json_body["class"]
        )


class IBMDedicatedHostProfile(db.Model):
    """
    Model for Dedicated host profile
    """
    ID_KEY = "id"
    NAME_KEY = "name"
    REGION_KEY = "region"
    HREF_KEY = "href"
    FAMILY_KEY = "family"
    CLASS_KEY = "class"
    SOCKET_COUNT_KEY = "socket_count"
    MEMORY_KEY = "memory"
    VCPU_ARCH_KEY = "vcpu_architecture"
    VCPU_COUNT_KEY = "vcpu_count"
    DISKS_KEY = "disks"
    DEDICATED_HOSTS_KEY = "dedicated_hosts"
    SUPPORTED_INSTANCE_PROFILES_KEY = "supported_instance_profiles"

    __tablename__ = "ibm_dedicated_host_profiles"
    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    region = Column(String(128), nullable=False)
    href = Column(Text)
    family = Column(Enum("balanced", "memory", "compute"))
    class_ = Column('class', String(20))
    socket_count = Column(JSON)
    memory = Column(JSON)  # Play around with properties for this
    vcpu_architecture = Column(JSON)  # Play around with properties for this
    vcpu_count = Column(JSON)  # Play around with properties for this
    disks = Column(JSON)  # Play around with properties for this

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)

    dedicated_hosts = relationship(
        "IBMDedicatedHost", backref="ibm_dedicated_host_profile", cascade="all, delete-orphan", lazy="dynamic"
    )
    supported_instance_profiles = relationship(
        "IBMInstanceProfile", secondary=ibm_dh_profile_supported_instance_profiles,
        backref="ibm_dedicated_host_profiles", lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint(
            name, region, cloud_id, name="uix_ibm_dh_profile_name_region_cloudid"
        ),
    )

    def __init__(
            self, name, region, href=None, family=None, class_=None, socket_count=None, memory=None,
            vcpu_architecture=None, vcpu_count=None, disks=None, cloud_id=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.href = href
        self.family = family
        self.class_ = class_
        self.socket_count = socket_count
        self.memory = memory
        self.vcpu_architecture = vcpu_architecture
        self.vcpu_count = vcpu_count
        self.disks = disks
        self.cloud_id = cloud_id

    @classmethod
    def from_ibm_json(cls, json_body):
        """
        Return an object of the class created from the provided JSON body
        """
        return cls(
            name=json_body["name"],
            region=json_body["href"].split("//")[1].split(".")[0],
            href=json_body["href"],
            family=json_body["family"],
            class_=json_body["class"],
            socket_count=json_body["socket_count"],
            memory=json_body["memory"],
            vcpu_architecture=json_body["vcpu_architecture"],
            vcpu_count=json_body["vcpu_count"],
            disks=json_body["disks"]
        )

    def update_from_obj(self, updated_obj, updated_supported_instance_profiles_list):
        """
        Update an existing object of the class from an updated one
        """
        from doosra.models import IBMInstanceProfile

        assert isinstance(updated_obj, IBMDedicatedHostProfile)
        self.name = updated_obj.name
        self.region = updated_obj.region
        self.href = updated_obj.href
        self.family = updated_obj.family
        self.class_ = updated_obj.class_
        self.memory = updated_obj.memory
        self.socket_count = updated_obj.socket_count
        self.vcpu_architecture = updated_obj.vcpu_architecture
        self.vcpu_count = updated_obj.vcpu_count
        self.disks = updated_obj.disks

        updated_sip_name_obj_dict = {}
        for updated_sip_relation in updated_supported_instance_profiles_list:
            updated_sip_name_obj_dict[updated_sip_relation.name] = updated_sip_relation

        sip_names_to_remove_relation_with = []
        for db_supported_instance_profile in self.supported_instance_profiles.all():
            if db_supported_instance_profile.name not in updated_sip_name_obj_dict:
                sip_names_to_remove_relation_with.append(db_supported_instance_profile.name)

        if sip_names_to_remove_relation_with:
            for instance_profile_to_remove_relation_with in db.session.query(IBMInstanceProfile).filter(
                    IBMInstanceProfile.cloud_id == self.cloud_id,
                    IBMInstanceProfile.name.in_(sip_names_to_remove_relation_with)
            ).all():
                instance_profile_to_remove_relation_with.ibm_dedicated_host_profiles.remove(self)
                db.session.commit()

        db_sip_names = [db_sip.name for db_sip in self.supported_instance_profiles.all()]
        for updated_sip_relation_name, updated_sip_relation_obj in updated_sip_name_obj_dict.items():
            if updated_sip_relation_name not in db_sip_names:
                self.supported_instance_profiles.append(updated_sip_name_obj_dict[updated_sip_relation_name])
                db.session.commit()

        db.session.commit()

    def to_json(self):
        """
        Return a JSON representation of the object
        """
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.REGION_KEY: self.region,
            # self.HREF_KEY: self.href,
            self.FAMILY_KEY: self.family,
            self.CLASS_KEY: self.class_,
            self.SOCKET_COUNT_KEY: self.socket_count,
            self.MEMORY_KEY: self.memory,
            self.VCPU_ARCH_KEY: self.vcpu_architecture,
            self.VCPU_COUNT_KEY: self.vcpu_count,
            self.DISKS_KEY: self.disks,
            self.DEDICATED_HOSTS_KEY:
                [{self.ID_KEY: dedicated_host.id} for dedicated_host in self.dedicated_hosts.all()],
            self.SUPPORTED_INSTANCE_PROFILES_KEY: [sip.to_json() for sip in self.supported_instance_profiles.all()]

        }


class IBMDedicatedHostDisk(db.Model):
    """
    Model for Dedicated host disk
    """
    ID_KEY = "id"
    NAME_KEY = "name"
    ZONE_KEY = "zone"
    RESOURCE_ID_KEY = "resource_id"
    HREF_KEY = "href"
    SIZE_KEY = "size"
    AVAILABLE_KEY = "available"
    INTERFACE_TYPE_KEY = "interface_type"
    PROVISIONABLE_KEY = "provisionable"
    SUPPORTED_INSTANCE_INTERFACE_TYPES_KEY = "supported_instance_interface_types"
    LIFECYCLE_STATE_KEY = "lifecycle_state"

    __tablename__ = "ibm_dedicated_host_disks"
    # instance_disks missing. Should be relationship. Currently IBMInstance does not have a disks relationship, skipping
    # resource_type missing. Not needed I guess
    id = Column(String(32), primary_key=True)
    name = Column(String(255))
    zone = Column(String(20), nullable=False)
    resource_id = Column(String(64))
    href = Column(Text)
    size = Column(Integer)
    available = Column(Integer)
    interface_type = Column(Enum("nvme"), default="nvme")
    provisionable = Column(Boolean, default=True)
    supported_instance_interface_types = Column(JSON)
    lifecycle_state = Column(
        Enum("deleting", "failed", "pending", "stable", "updating", "waiting", "suspended"), default="stable"
    )

    dedicated_host_id = Column(String(32), ForeignKey("ibm_dedicated_hosts.id"))

    def __init__(
            self, name, zone, resource_id, href, size, available, interface_type, provisionable,
            supported_instance_interface_types, lifecycle_state=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.zone = zone
        self.resource_id = resource_id
        self.href = href
        self.size = size
        self.available = available
        self.interface_type = interface_type
        self.provisionable = provisionable
        self.supported_instance_interface_types = supported_instance_interface_types
        self.lifecycle_state = lifecycle_state

    def to_json(self):
        """
        Return a JSON representation of the object
        """
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.ZONE_KEY: self.zone,
            self.RESOURCE_ID_KEY: self.resource_id,
            self.HREF_KEY: self.href,
            self.SIZE_KEY: self.size,
            self.AVAILABLE_KEY: self.available,
            self.INTERFACE_TYPE_KEY: self.interface_type,
            self.PROVISIONABLE_KEY: self.provisionable,
            self.SUPPORTED_INSTANCE_INTERFACE_TYPES_KEY: self.supported_instance_interface_types,
            self.LIFECYCLE_STATE_KEY: self.lifecycle_state
        }
