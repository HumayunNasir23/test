import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    PrimaryKeyConstraint,
    String,
    Text, desc,
)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import UniqueConstraint

from doosra import db
from doosra.common.consts import (
    classical_vpc_image_dictionary,
    CREATION_PENDING,
    CREATED,
    ERROR_CREATING, PENDING,
)
from doosra.common.utils import get_image_key
from doosra.models import IBMTask

ibm_instance_keys = db.Table(
    "ibm_instance_keys",
    Column("instance_id", String(32), ForeignKey("ibm_instances.id"), nullable=False),
    Column("key_id", String(32), ForeignKey("ibm_ssh_keys.id"), nullable=False),
    PrimaryKeyConstraint("instance_id", "key_id"),
)

ibm_network_interfaces_security_groups = db.Table(
    "ibm_network_interfaces_security_groups",
    Column(
        "network_interface_id",
        String(32),
        ForeignKey("ibm_network_interfaces.id"),
        nullable=False,
    ),
    Column(
        "security_group_id",
        String(32),
        ForeignKey("ibm_security_groups.id"),
        nullable=False,
    ),
    PrimaryKeyConstraint("network_interface_id", "security_group_id"),
)


class IBMInstance(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    REGION_KEY = "region"
    ZONE_KEY = "zone"
    STATUS_KEY = "status"
    STATE_KEY = "state"
    INSTANCE_STATUS_KEY = "instance_status"
    VPC_KEY = "vpc"
    IMAGE_KEY = "image"
    MIG_INFO_KEY = "mig_info"
    INSTANCE_PROFILE_KEY = "instance_profile"
    SSH_KEY = "ssh_keys"
    USER_DATA_KEY = "user_data"
    NETWORK_INTERFACE_KEY = "network_interfaces"
    PRIMARY_NETWORK_INTERFACE_KEY = "primary_network_interface"
    BOOT_VOLUME_ATTACHMENT_KEY = "boot_volume_attachment"
    VOLUME_ATTACHMENT_KEY = "volume_attachments"
    CLOUD_ID_KEY = "cloud_id"
    IS_VOLUME_MIGRATION = "data_migration"
    CLASSICAL_INSTANCE_ID_KEY = "classical_instance_id"
    ORIGINAL_IMAGE_KEY = "original_image"
    ORIGINAL_OPERATING_SYSTEM_NAME_KEY = "original_operating_system_name"
    VOLUME_MIGRATION_STATUS_KEY = "volume_migration_status"
    INSTANCE_TYPE_KEY = "instance_type"
    DATA_CENTER_KEY = "data_center"
    MESSAGE_KEY = "message"
    AUTO_SCALE_GROUP_KEY = "auto_scale_group"
    NETWORK_ATTACHED_STORAGES_KEY = "network_attached_storages"
    REPORT_TASK_ID = "report_task_id"
    AUTO_SCALE_GROUP = "auto_scale_group"
    SECONDARY_VOLUME_MIGRATION_TASK_ID_KEY = "secondary_volume_migration_task_id"
    DEDICATED_HOST_ID_KEY = "dedicated_host_id"
    DEDICATED_HOST_GROUP_ID_KEY = "dedicated_host_group_id"

    __tablename__ = "ibm_instances"

    id = Column(String(32), primary_key=True)
    resource_id = Column(String(64))
    name = Column(String(255), nullable=False)
    region = Column(String(255), nullable=True)
    zone = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    state = Column(String(50), nullable=True)
    instance_status = Column(String(50), nullable=True)
    user_data = Column(Text)
    classical_instance_id = Column(Integer, nullable=True)
    is_volume_migration = Column(Boolean, nullable=False, default=False)
    nas_migration_enabled = Column(Boolean, nullable=False, default=False)
    instance_type = Column(Enum("PUBLIC", "PRIVATE", "DEDICATED"))
    data_center = Column(String(255), nullable=True)
    auto_scale_group = Column(String(255), nullable=True)
    original_operating_system_name = Column(String(255), nullable=True)
    network_attached_storages = Column(JSON, nullable=True)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))
    vpc_id = Column(String(32), ForeignKey("ibm_vpc_networks.id"), nullable=False)
    instance_profile_id = Column(String(32), ForeignKey("ibm_instance_profiles.id"), nullable=False)
    image_id = Column(String(32), ForeignKey("ibm_images.id"), nullable=True)
    dedicated_host_id = Column(String(32), ForeignKey("ibm_dedicated_hosts.id"), nullable=True)
    dedicated_host_group_id = Column(String(32), ForeignKey("ibm_dedicated_host_groups.id"), nullable=True)

    ssh_keys = relationship("IBMSshKey", secondary=ibm_instance_keys, backref=backref("ibm_instances"), lazy="dynamic")
    pool_members = relationship("IBMPoolMember", backref="instance", lazy="dynamic")
    network_interfaces = relationship(
        "IBMNetworkInterface", backref="ibm_instance", cascade="all, delete-orphan", lazy="dynamic")
    volume_attachments = relationship(
        "IBMVolumeAttachment", backref="ibm_instance", cascade="all, delete-orphan", lazy="dynamic")
    secondary_volume_mig_task = db.relationship(
        'SecondaryVolumeMigrationTask', uselist=False, backref="ibm_instance", cascade="all, delete-orphan")
    instance_tasks = db.relationship(
        'IBMInstanceTasks', backref="ibm_instance", cascade="all, delete-orphan", lazy="dynamic")

    __table_args__ = (UniqueConstraint(name, vpc_id, cloud_id, name="uix_ibm_name_vpc_id_cloud_id_region"),)

    def __init__(
            self,
            name,
            zone,
            region,
            instance_type=None,
            data_center=None,
            resource_id=None,
            status=CREATION_PENDING,
            state=None,
            user_data=None,
            cloud_id=None,
            instance_status=None,
            is_volume_migration=False,
            vpc_id=None,
            classical_instance_id=None,
            auto_scale_group=None,
            network_attached_storages=None,
            original_operating_system_name=None,
            nas_migration_enabled=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.status = status
        self.state = state
        self.zone = zone
        self.user_data = user_data
        self.resource_id = resource_id
        self.cloud_id = cloud_id
        self.instance_status = instance_status
        self.is_volume_migration = is_volume_migration
        self.vpc_id = vpc_id
        self.classical_instance_id = classical_instance_id
        self.instance_type = instance_type
        self.data_center = data_center
        self.auto_scale_group = auto_scale_group
        self.network_attached_storages = network_attached_storages
        self.original_operating_system_name = original_operating_system_name
        self.nas_migration_enabled = nas_migration_enabled

    def set_error_status(self):
        if not self.status == CREATED:
            self.status = ERROR_CREATING
            db.session.commit()

        for obj in self.ssh_keys.all():
            obj.set_error_status()

    def make_copy(self):
        obj = IBMInstance(
            name=self.name,
            region=self.region,
            zone=self.zone,
            resource_id=self.resource_id,
            status=self.status,
            state=self.state,
            user_data=self.user_data,
            cloud_id=self.cloud_id,
            instance_status=self.instance_status,
            is_volume_migration=self.is_volume_migration,
            classical_instance_id=self.classical_instance_id,
            instance_type=self.instance_type,
            data_center=self.data_center,
            auto_scale_group=self.auto_scale_group,
            network_attached_storages=self.network_attached_storages,
            original_operating_system_name=self.original_operating_system_name
        )
        for key in self.ssh_keys.all():
            obj.ssh_keys.append(key.make_copy())

        for interface in self.network_interfaces.all():
            obj.network_interfaces.append(interface.make_copy())

        for vol_attachment in self.volume_attachments.all():
            obj.volume_attachments.append(vol_attachment.make_copy())

        if self.ibm_image:
            obj.ibm_image = self.ibm_image.make_copy()

        if self.ibm_instance_profile:
            obj.ibm_instance_profile = self.ibm_instance_profile.make_copy()

        if self.ibm_resource_group:
            obj.ibm_resource_group = self.ibm_resource_group.make_copy()

        return obj

    def get_existing_from_db(self, vpc=None):
        if vpc:
            return db.session.query(self.__class__).filter_by(
                name=self.name, region=self.region, cloud_id=self.cloud_id, vpc_id=vpc.id).first()

        return db.session.query(self.__class__).filter_by(
            name=self.name, region=self.region, cloud_id=self.cloud_id, vpc_id=self.vpc_id).first()

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not ((self.name == other.name) and (self.zone == other.zone) and (self.region == other.region) and
                (self.resource_id == other.resource_id) and (self.user_data == other.user_data) and
                (self.state == other.state) and (self.instance_status == other.instance_status)):
            return False

        if not len(self.ssh_keys.all()) == len(other.ssh_keys.all()):
            return False

        if not len(self.network_interfaces.all()) == len(other.network_interfaces.all()):
            return False

        if not len(self.volume_attachments.all()) == len(other.volume_attachments.all()):
            return False

        for ssh_key in self.ssh_keys.all():
            found = False
            for ssh_key_ in other.ssh_keys.all():
                if ssh_key.name == ssh_key_.name:
                    found = True

            if not found:
                return False

        for network_interface in self.network_interfaces.all():
            found = False
            for network_interface_ in other.network_interfaces.all():
                if network_interface.params_eq(network_interface_):
                    found = True

            if not found:
                return False

        for volume_attachment in self.volume_attachments.all():
            found = False
            for volume_attachment_ in other.volume_attachments.all():
                if volume_attachment.params_eq(volume_attachment_):
                    found = True

            if not found:
                return False

        if (self.ibm_image and not other.ibm_image) or (not self.ibm_image and other.ibm_image):
            return False

        if self.ibm_image and other.ibm_image:
            if not self.ibm_image.params_eq(other.ibm_image):
                return False

        if (self.ibm_instance_profile and not other.ibm_instance_profile) or \
                (not self.ibm_instance_profile and other.ibm_instance_profile):
            return False

        if self.ibm_instance_profile and other.ibm_instance_profile:
            if not self.ibm_instance_profile.params_eq(other.ibm_instance_profile):
                return False

        if (self.ibm_resource_group and not other.ibm_resource_group) or \
                (not self.ibm_resource_group and other.ibm_resource_group):
            return False

        if self.ibm_resource_group and other.ibm_resource_group:
            if not self.ibm_resource_group.params_eq(other.ibm_resource_group):
                return False

        return True

    def add_update_db(self, vpc):
        existing = self.get_existing_from_db(vpc)
        if not existing:
            volume_attachments, network_interfaces, ssh_keys = (
                self.volume_attachments.all(),
                self.network_interfaces.all(),
                self.ssh_keys.all())
            ibm_image, ibm_instance_profile = self.ibm_image, self.ibm_instance_profile
            ibm_resource_group = self.ibm_resource_group
            self.volume_attachments, self.network_interfaces, self.ssh_keys = list(), list(), list()
            self.ibm_image, self.ibm_instance_profile, self.ibm_resource_group = None, None, None

            if ibm_instance_profile:
                ibm_instance_profile = ibm_instance_profile.add_update_db()

            if ibm_image:
                ibm_image = ibm_image.add_update_db()

            if ibm_resource_group:
                ibm_resource_group = ibm_resource_group.add_update_db()

            self.ibm_vpc_network = vpc
            self.ibm_instance_profile = ibm_instance_profile
            self.ibm_image = ibm_image
            self.ibm_resource_group = ibm_resource_group
            db.session.add(self)
            db.session.commit()

            for network_interface in network_interfaces:
                network_interface.add_update_db(self)
                db.session.commit()

            for volume_attachment in volume_attachments:
                volume_attachment.add_update_db(self)
                db.session.commit()

            for ssh_key in ssh_keys:
                self.ssh_keys.append(ssh_key.add_update_db())
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.status = self.status
            existing.region = self.region
            existing.instance_status = self.instance_status
            existing.zone = self.zone
            existing.resource_id = self.resource_id
            existing.user_data = self.user_data
            db.session.commit()

            for volume_attachment in existing.volume_attachments.all():
                found = False
                for volume_attachment_ in self.volume_attachments.all():
                    if volume_attachment.name == volume_attachment_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(volume_attachment)
                    db.session.commit()

            for ssh_key in existing.ssh_keys.all():
                found = False
                for ssh_key_ in self.ssh_keys.all():
                    if ssh_key.name == ssh_key_.name:
                        found = True
                        break

                if not found:
                    existing.ssh_keys.remove(ssh_key)
                    db.session.commit()

            for network_interface in existing.network_interfaces.all():
                found = False
                for network_interface_ in self.network_interfaces.all():
                    if network_interface.name == network_interface_.name:
                        found = True
                        break

                if not found:
                    db.session.delete(network_interface)
                    db.session.commit()

            volume_attachments, network_interfaces, ssh_keys = (
                self.volume_attachments.all(),
                self.network_interfaces.all(),
                self.ssh_keys.all(),
            )
            ibm_image, ibm_instance_profile = self.ibm_image, self.ibm_instance_profile
            ibm_resource_group = self.ibm_resource_group
            self.volume_attachments, self.network_interfaces, self.ssh_keys = list(), list(), list()
            self.ibm_image, self.ibm_resource_group, self.ibm_instance_profile = None, None, None

            for network_interface in network_interfaces:
                network_interface.add_update_db(existing)

            for volume_attachment in volume_attachments:
                volume_attachment.add_update_db(existing)

            existing.ssh_keys = list()
            for ssh_key in ssh_keys:
                existing.ssh_keys.append(ssh_key.add_update_db())
                db.session.commit()

            if ibm_image:
                existing.ibm_image = ibm_image.add_update_db()
            else:
                existing.ibm_image = None
            db.session.commit()

            if ibm_instance_profile:
                existing.ibm_instance_profile = ibm_instance_profile.add_update_db()
            else:
                existing.ibm_instance_profile = None
            db.session.commit()

            if ibm_resource_group:
                existing.ibm_resource_group = ibm_resource_group.add_update_db()
            else:
                existing.ibm_resource_group = None
            db.session.commit()

        return existing

    def to_json(self):
        boot_volume_attachment = [
            attachment.to_json()
            for attachment in self.volume_attachments.all()
            if attachment.type == "boot"
        ]
        primary_interface = [
            interface.to_json()
            for interface in self.network_interfaces.all()
            if interface.is_primary
        ]
        instance_tasks_ = self.instance_tasks.all()

        json_data = {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.REGION_KEY: self.region,
            self.ZONE_KEY: self.zone,
            self.STATUS_KEY: self.status,
            self.INSTANCE_STATUS_KEY: self.instance_status.upper() if self.instance_status else None,
            self.IMAGE_KEY: self.ibm_image.to_json() if self.ibm_image else {},
            self.MIG_INFO_KEY: instance_tasks_[0].to_json() if instance_tasks_ else {},
            self.INSTANCE_PROFILE_KEY: self.ibm_instance_profile.to_json() if self.ibm_instance_profile else "",
            self.SSH_KEY: [key.to_json() for key in self.ssh_keys.all()],
            self.NETWORK_INTERFACE_KEY: [interface.to_json() for interface in self.network_interfaces.all()],
            self.USER_DATA_KEY: self.user_data,
            self.STATE_KEY: self.state,
            self.BOOT_VOLUME_ATTACHMENT_KEY: boot_volume_attachment[0] if boot_volume_attachment else {},
            self.VOLUME_ATTACHMENT_KEY: [
                attachment.to_json() for attachment in self.volume_attachments.all() if attachment.type == "data"],
            self.CLOUD_ID_KEY: self.cloud_id,
            self.VPC_KEY: {
                self.ID_KEY: self.ibm_vpc_network.id,
                self.NAME_KEY: self.ibm_vpc_network.name} if self.ibm_vpc_network else None,
            self.PRIMARY_NETWORK_INTERFACE_KEY: primary_interface[0] if primary_interface else None,
            self.CLASSICAL_INSTANCE_ID_KEY: self.classical_instance_id if
            hasattr(self, "classical_instance_id") else None,
            self.IS_VOLUME_MIGRATION: self.is_volume_migration,
            self.VOLUME_MIGRATION_STATUS_KEY: (
                self.secondary_volume_mig_task.status if self.secondary_volume_mig_task else None
            ),
            self.SECONDARY_VOLUME_MIGRATION_TASK_ID_KEY: self.get_secondary_volume_migration_task_id(),
            self.INSTANCE_TYPE_KEY: self.instance_type,
            self.DATA_CENTER_KEY: self.data_center,
            self.AUTO_SCALE_GROUP_KEY: self.auto_scale_group,
            self.NETWORK_ATTACHED_STORAGES_KEY: self.network_attached_storages,
            self.REPORT_TASK_ID: self.get_resource_task_id(),
            self.ORIGINAL_OPERATING_SYSTEM_NAME_KEY: self.original_operating_system_name,
            self.ORIGINAL_IMAGE_KEY: instance_tasks_[0].vpc_image_name or instance_tasks_[
                0].public_image if instance_tasks_ else "",
            self.DEDICATED_HOST_ID_KEY: self.ibm_dedicated_host.id if self.ibm_dedicated_host else None,
            self.DEDICATED_HOST_GROUP_ID_KEY:
                self.ibm_dedicated_host_group.id if self.ibm_dedicated_host_group else None,
        }
        return json_data

    def to_json_body(self):
        json_body = {
            "name": self.name,
            "zone": {"name": self.zone},
            "user_data": self.user_data or "",
            "resource_group": {"id": self.ibm_resource_group.resource_id if self.ibm_resource_group else None},
            "vpc": {"id": self.ibm_vpc_network.resource_id},
            "image": {"id": self.ibm_image.resource_id},
            "profile": {"name": self.ibm_instance_profile.name},
            "keys": [{"id": key.resource_id} for key in self.ssh_keys.all()],
            "primary_network_interface": [
                interface.to_json_body() for interface in self.network_interfaces.all() if interface.is_primary][0],
            "network_interfaces": [
                interface.to_json_body() for interface in self.network_interfaces.all() if not interface.is_primary],
            "volume_attachments": [
                attachment.to_json_body() for attachment in self.volume_attachments.all() if attachment.type == "data"],
            "boot_volume_attachment": [
                attachment.to_json_body() for attachment in self.volume_attachments.all()
                if attachment.type == "boot"][0] if self.volume_attachments.all() else [],
        }
        del json_body["boot_volume_attachment"]["volume"]["capacity"]
        if self.ibm_dedicated_host:
            json_body["placement_target"] = {
                "id": self.ibm_dedicated_host.resource_id
            }
        elif self.ibm_dedicated_host_group:
            json_body["placement_target"] = {
                "id": self.ibm_dedicated_host_group.resource_id
            }
        return json_body

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
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
            status = "CREATING"
        elif json_body["status"] in [
            "starting", "pausing", "paused", "resuming", "restarting", "stopping", "stopped", "running"
        ]:
            status = "CREATED"
        elif json_body["status"] == "failed":
            status = "ERROR_"

        assert status

        ibm_instance = IBMInstance(
            name=json_body["name"], zone=json_body["zone"]["name"], region=region, resource_id=json_body["id"],
            instance_status=json_body["status"], status=status
        )

        return ibm_instance

    def get_secondary_volume_migration_task_id(self):
        """
        This method returns secondary volume migration task id.
        """
        return self.secondary_volume_mig_task.id if self.secondary_volume_mig_task else None


class IBMInstanceProfile(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    FAMILY_KEY = "family"
    ARCHITECTURE_KEY = "architecture"
    STATUS_KEY = "status"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_instance_profiles"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    family = Column(Enum("BALANCED", "COMPUTE", "MEMORY", "GPU", "HIGH-MEMORY", "VERY-HIGH-MEMORY", "GPU-V100"), nullable=True)
    architecture = Column(Enum("power", "amd64", "s390x"), default="amd64", nullable=True)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)

    instances = relationship(
        "IBMInstance",
        backref="ibm_instance_profile",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(name, cloud_id, name="uix_ibm_instance_profile_cloud_id"),
    )

    def __init__(self, name, family=None, cloud_id=None, architecture=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.architecture = architecture
        self.family = family.upper() if family else None
        self.cloud_id = cloud_id

    def make_copy(self):

        return IBMInstanceProfile(
            name=self.name, family=self.family, cloud_id=self.cloud_id, architecture=self.architecture
        )

    def get_existing_from_db(self):

        return (
            db.session.query(self.__class__)
                .filter_by(name=self.name, cloud_id=self.cloud_id)
                .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not ((self.name == other.name) and (self.family == other.family) and
                (self.architecture == other.architecture)):
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
            existing.family = self.family
            existing.architecture = self.architecture
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.FAMILY_KEY: self.family,
            self.ARCHITECTURE_KEY: self.architecture,
        }

    def to_report_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: PENDING,
            self.MESSAGE_KEY: ""
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        instance_profile = IBMInstanceProfile(
            name=json_body["name"], family=json_body["family"], architecture=json_body["vcpu_architecture"]["value"]
        )

        return instance_profile


class IBMImage(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    ARCHITECTURE_KEY = "architecture"
    VISIBILITY_KEY = "visibility"
    OPERATING_SYSTEM_KEY = "operating_systems"
    IMAGE_TEMPLATE_PATH_KEY = "image_template_path"
    REGION_KEY = "region"
    STATUS_KEY = "status"
    SIZE_KEY = "size"
    CLASSICAL_IMAGE_NAME = "classical_image_name"
    VPC_IMAGE_NAME = "vpc_image_name"
    CLOUD_ID_KEY = "cloud_id"

    __tablename__ = "ibm_images"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    resource_id = Column(String(64))
    visibility = Column(Enum("private", "public"))
    status = Column(String(50), nullable=False)
    image_template_path = Column(String(255))
    region = Column(String(255))
    size = Column(String(255))
    vpc_image_name = Column(String(255))

    resource_group_id = Column(String(32), ForeignKey("ibm_resource_groups.id"))
    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    operating_system_id = Column(String(32), ForeignKey("ibm_operating_systems.id"))

    instances = relationship("IBMInstance", backref="ibm_image", lazy="dynamic")

    __table_args__ = (UniqueConstraint(
        name, cloud_id, region, visibility, name="uix_ibm_image_name_region_visibility_cloud_id"),)

    def __init__(self, name, visibility=None, resource_id=None, cloud_id=None, resource_group_id=None, status=None,
                 image_template_path=None, region=None, size=None, vpc_image_name=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.visibility = visibility
        self.resource_id = resource_id
        self.cloud_id = cloud_id
        self.resource_group_id = resource_group_id
        self.status = status or CREATION_PENDING
        self.image_template_path = image_template_path
        self.region = region
        self.size = size
        self.vpc_image_name = vpc_image_name

    def make_copy(self):
        ibm_image = IBMImage(
            name=self.name, visibility=self.visibility, resource_id=self.resource_id, cloud_id=self.cloud_id,
            status=self.status, image_template_path=self.image_template_path, region=self.region, size=self.size,
            vpc_image_name=self.vpc_image_name)

        if self.ibm_resource_group:
            ibm_image.ibm_resource_group = self.ibm_resource_group.make_copy()

        if self.operating_system:
            ibm_image.operating_system = self.operating_system.make_copy()

        return ibm_image

    def get_existing_from_db(self):
        return (
            db.session.query(self.__class__)
                .filter_by(
                name=self.name,
                region=self.region,
                visibility=self.visibility,
                cloud_id=self.cloud_id,
            )
                .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
                (self.name == other.name)
                and (self.resource_id == other.resource_id)
                and (self.visibility == other.visibility)
                and (self.size == other.size)
                and (self.region == other.region)
                and (self.image_template_path == other.image_template_path)
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

        if (self.operating_system and not other.operating_system) or (
                not self.operating_system and other.operating_system
        ):
            return False

        if self.operating_system and other.operating_system:
            if not self.operating_system.params_eq(other.operating_system):
                return False

        return True

    def add_update_db(self):
        existing = self.get_existing_from_db()
        if not existing:
            ibm_resource_group, operating_system = (
                self.ibm_resource_group,
                self.operating_system,
            )
            self.ibm_resource_group, self.operating_system = None, None

            db.session.add(self)
            db.session.commit()

            if ibm_resource_group:
                ibm_resource_group = ibm_resource_group.make_copy().add_update_db()

            if operating_system:
                operating_system = operating_system.make_copy().add_update_db()

            self.ibm_resource_group = ibm_resource_group
            self.operating_system = operating_system
            db.session.commit()
            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.resource_id = self.resource_id
            existing.status = self.status
            existing.region = self.region
            existing.size = self.size
            existing.visibility = self.visibility
            existing.image_template_path = self.image_template_path
            db.session.commit()

            ibm_resource_group, operating_system = (
                self.ibm_resource_group,
                self.operating_system,
            )
            self.ibm_resource_group, self.operating_system = None, None

            if ibm_resource_group:
                existing.ibm_resource_group = ibm_resource_group.add_update_db()
            else:
                existing.ibm_resource_group = None
            db.session.commit()

            if operating_system:
                existing.operating_system = operating_system.add_update_db()
            else:
                existing.operating_system = None
            db.session.commit()

        return existing

    def to_json(self):
        image_name = classical_vpc_image_dictionary.get(self.name)
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.IMAGE_TEMPLATE_PATH_KEY: self.image_template_path,
            self.REGION_KEY: self.region,
            self.VISIBILITY_KEY: self.visibility,
            self.STATUS_KEY: self.status,
            self.SIZE_KEY: self.size,
            self.CLASSICAL_IMAGE_NAME: get_image_key(
                classical_vpc_image_dictionary, self.name
            ),
            self.VPC_IMAGE_NAME: image_name[0] if image_name else self.vpc_image_name,
            self.OPERATING_SYSTEM_KEY: self.operating_system.to_json()
            if self.operating_system
            else "",
            self.CLOUD_ID_KEY: self.cloud_id
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "operating_system": {
                "name": self.operating_system.name if self.operating_system else ""
            },
            "file": {"href": self.image_template_path},
            "resource_group": {
                "id": self.ibm_resource_group.resource_id
                if self.ibm_resource_group
                else ""
            },
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
        ibm_image = IBMImage(
            name=json_body["name"], visibility=json_body["visibility"], resource_id=json_body["id"], status=status,
            region=region, size=json_body["file"].get("size")
        )

        if json_body.get("operating_system"):
            ibm_image.operating_system = IBMOperatingSystem.from_ibm_json_body(json_body["operating_system"])

        return ibm_image


class IBMOperatingSystem(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    ARCHITECTURE_KEY = "architecture"
    FAMILY_KEY = "family"
    VENDOR_KEY = "vendor"
    VERSION_KEY = "version"

    __tablename__ = "ibm_operating_systems"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    architecture = Column(String(255))
    family = Column(String(255))
    vendor = Column(String(255))
    version = Column(String(255))

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)

    images = relationship(
        "IBMImage",
        backref="operating_system",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint(name, cloud_id, name="uix_ibm_operation_system_name_cloud_id"),
    )

    def __init__(
            self, name, architecture=None, family=None, vendor=None, version=None, cloud_id=None, image_id=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.architecture = architecture
        self.family = family
        self.vendor = vendor
        self.version = version
        self.cloud_id = cloud_id
        self.image_id = image_id

    def make_copy(self):
        return IBMOperatingSystem(
            name=self.name,
            architecture=self.architecture,
            family=self.family,
            vendor=self.vendor,
            version=self.version,
            cloud_id=self.cloud_id,
        )

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
                and (self.architecture == other.architecture)
                and (self.family == other.family)
                and (self.vendor == other.vendor)
                and (self.version == other.version)
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
            existing.architecture = self.architecture
            existing.family = self.family
            existing.vendor = self.vendor
            existing.version = self.version
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.ARCHITECTURE_KEY: self.architecture,
            self.FAMILY_KEY: self.family,
            self.VENDOR_KEY: self.vendor,
            self.VERSION_KEY: self.version,
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        ibm_os = IBMOperatingSystem(
            name=json_body["name"], architecture=json_body["architecture"], family=json_body["family"],
            vendor=json_body["vendor"], version=json_body["version"]
        )

        return ibm_os


class IBMNetworkInterface(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    SUBNET_KEY = "subnet"
    SECURITY_GROUP_KEY = "security_groups"
    INSTANCE_KEY = "instance_id"
    PRIVATE_IP_KEY = "private_ip"
    FLOATING_IP_KEY = "floating_ip"

    __tablename__ = "ibm_network_interfaces"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    private_ip = Column(String(255))
    resource_id = Column(String(64))

    subnet_id = Column(String(32), ForeignKey("ibm_subnets.id"))
    instance_id = Column(String(32), ForeignKey("ibm_instances.id"), nullable=False)

    floating_ip = relationship(
        "IBMFloatingIP", backref="ibm_network_interface", uselist=False
    )
    security_groups = relationship(
        "IBMSecurityGroup",
        secondary=ibm_network_interfaces_security_groups,
        backref=backref("network_interfaces"),
        lazy="dynamic",
    )
    __table_args__ = (
        UniqueConstraint(name, instance_id, name="uix_ibm_interface_name_instance_id"),
    )

    def __init__(self, name, is_primary=False, resource_id=None, private_ip=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.private_ip = private_ip
        self.resource_id = resource_id
        self.is_primary = is_primary

    def make_copy(self):
        obj = IBMNetworkInterface(
            self.name, self.is_primary, self.resource_id, self.private_ip
        )
        if self.ibm_subnet:
            obj.ibm_subnet = self.ibm_subnet.make_copy()

        for security_group in self.security_groups:
            obj.security_groups.append(security_group.make_copy())

        if self.floating_ip:
            obj.floating_ip = self.floating_ip.make_copy()

        return obj

    def get_existing_from_db(self, instance=None):
        if instance:
            return (
                db.session.query(self.__class__)
                    .filter_by(name=self.name, instance_id=instance.id)
                    .first()
            )
        return (
            db.session.query(self.__class__)
                .filter_by(name=self.name, instance_id=self.instance_id)
                .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
                (self.name == other.name)
                and (self.resource_id == other.resource_id)
                and (self.is_primary == other.is_primary)
                and (self.private_ip == other.private_ip)
        ):
            return False

        if (self.ibm_subnet and not other.ibm_subnet) or (
                not self.ibm_subnet and other.ibm_subnet
        ):
            return False

        if self.ibm_subnet and other.ibm_subnet:
            if not self.ibm_subnet.params_eq(other.ibm_subnet):
                return False

        if not len(self.security_groups.all()) == len(other.security_groups.all()):
            return False

        if (self.floating_ip and not other.floating_ip) or (
                not self.floating_ip and other.floating_ip
        ):
            return False

        if self.floating_ip and other.floating_ip:
            if not self.floating_ip.params_eq(other.floating_ip):
                return False

        for security_group in self.security_groups.all():
            found = False
            for security_group_ in other.security_groups.all():
                if security_group.name == security_group_.name:
                    found = True

            if not found:
                return False

        return True

    def add_update_db(self, instance):
        existing = self.get_existing_from_db(instance)
        if not existing:
            ibm_subnet, security_groups, floating_ip = (
                self.ibm_subnet,
                self.security_groups.all(),
                self.floating_ip,
            )
            self.ibm_subnet, self.floating_ip = None, None
            self.security_groups = list()
            self.ibm_instance = instance
            db.session.add(self)
            db.session.commit()

            for security_group in security_groups:
                self.security_groups.append(
                    security_group.add_update_db(instance.ibm_vpc_network)
                )
                db.session.commit()

            if ibm_subnet:
                self.ibm_subnet = ibm_subnet.add_update_db(instance.ibm_vpc_network)
                db.session.commit()

            if floating_ip:
                self.floating_ip = floating_ip.add_update_db()
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.resource_id = self.resource_id
            existing.is_primary = self.is_primary
            existing.private_ip = self.private_ip
            db.session.commit()

            for security_group in existing.security_groups.all():
                found = False
                for security_group_ in self.security_groups.all():
                    if security_group.name == security_group_.name:
                        found = True
                        break

                if not found:
                    existing.security_groups.remove(security_group)
                    db.session.commit()

            ibm_subnet, security_groups, floating_ip = (
                self.ibm_subnet,
                self.security_groups.all(),
                self.floating_ip,
            )
            self.ibm_subnet, self.floating_ip = None, None
            self.security_groups = list()

            existing.security_groups = list()
            for security_group in security_groups:
                existing.security_groups.append(
                    security_group.add_update_db(instance.ibm_vpc_network)
                )
            db.session.commit()

            if ibm_subnet:
                existing.ibm_subnet = ibm_subnet.add_update_db(instance.ibm_vpc_network)
            else:
                existing.ibm_subnet = None
            db.session.commit()

            if floating_ip:
                existing.floating_ip = floating_ip.add_update_db()
            else:
                existing.floating_ip = None
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.PRIVATE_IP_KEY: self.private_ip,
            self.SUBNET_KEY: self.ibm_subnet.to_json() if self.ibm_subnet else "",
            self.SECURITY_GROUP_KEY: [
                security_group.id for security_group in self.security_groups
            ]
            if self.security_groups
            else [],
            self.INSTANCE_KEY: self.ibm_instance.id if self.ibm_instance else "",
            self.FLOATING_IP_KEY: self.floating_ip.to_json()
            if self.floating_ip
            else ""
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "subnet": {"id": self.ibm_subnet.resource_id},
            "security_groups": [
                {"id": security_group.resource_id}
                for security_group in self.security_groups
            ],
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        ibm_network_interface = IBMNetworkInterface(
            name=json_body["name"], resource_id=json_body["id"], private_ip=json_body["primary_ipv4_address"]
        )

        return ibm_network_interface


class IBMVolumeProfile(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    FAMILY_KEY = "family"
    GENERATION_KEY = "generation"
    REGION_KEY = "region"

    __tablename__ = "ibm_volume_profiles"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    family = Column(String(255))
    region = Column(String(255))
    generation = Column(String(255))

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)

    volumes = relationship(
        "IBMVolume",
        backref="volume_profile",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __init__(self, name, region, family=None, generation=None, cloud_id=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.region = region
        self.family = family
        self.generation = generation
        self.cloud_id = cloud_id

    def make_copy(self):
        return IBMVolumeProfile(
            name=self.name,
            region=self.region,
            family=self.family,
            generation=self.generation,
            cloud_id=self.cloud_id,
        )

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
                and (self.family == other.family)
                and (self.region == other.region)
                and (self.generation == other.generation)
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
            existing.family = self.family
            existing.region = self.region
            existing.generation = self.generation
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.FAMILY_KEY: self.family,
            self.REGION_KEY: self.region,
            self.GENERATION_KEY: self.generation,
        }

    def to_json_body(self):
        return {"name": self.name}

    @classmethod
    def from_ibm_json_body(cls, region, json_body):
        volume_profile = IBMVolumeProfile(
            name=json_body["name"], region=region, family=json_body.get("family")
        )

        return volume_profile


class IBMVolume(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    ENCRYPTION_KEY = "encryption"
    IOPS_KEY = "iops"
    REGION_KEY = "region"
    ZONE_KEY = "zone"
    CAPACITY_KEY = "capacity"
    PROFILE_KEY = "profile"
    STATUS_KEY = "status"
    ORIGINAL_CAPACITY_KEY = "original_capacity"
    MESSAGE_KEY = "message"

    __tablename__ = "ibm_volumes"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    resource_id = Column(String(64))
    region = Column(String(255), nullable=True)
    zone = Column(String(255), nullable=False)
    capacity = Column(Integer)
    encryption = Column(String(255))
    iops = Column(Integer)
    original_capacity = Column(Integer, nullable=True)

    cloud_id = Column(String(32), ForeignKey("ibm_clouds.id"), nullable=False)
    status = Column(String(50), nullable=False)
    volume_profile_id = Column(
        String(32), ForeignKey("ibm_volume_profiles.id"), nullable=False
    )
    volume_attachment_id = Column(
        String(32), ForeignKey("ibm_volume_attachments.id", ondelete='CASCADE'), nullable=True
    )
    __table_args__ = (
        UniqueConstraint(name, region, cloud_id, volume_attachment_id,
                         name="uix_ibm_volumes_name_region_cloud_id_vol_attachment_id"),
    )

    def __init__(
            self,
            name,
            capacity,
            zone,
            iops=None,
            encryption=None,
            resource_id=None,
            cloud_id=None,
            region=None,
            status=None,
            original_capacity=None
    ):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.capacity = capacity
        self.iops = iops
        self.region = region
        self.zone = zone
        self.encryption = encryption
        self.resource_id = resource_id
        self.cloud_id = cloud_id
        self.status = status or CREATION_PENDING
        self.original_capacity = original_capacity

    def make_copy(self):
        obj = IBMVolume(
            name=self.name,
            capacity=self.capacity,
            region=self.region,
            zone=self.zone,
            iops=self.iops,
            encryption=self.encryption,
            resource_id=self.resource_id,
            cloud_id=self.cloud_id,
            status=self.status,
        )

        if self.volume_profile:
            obj.volume_profile = self.volume_profile.make_copy()

        return obj

    def get_existing_from_db(self, volume_attachment=None):
        if volume_attachment:
            return (
                db.session.query(self.__class__)
                    .filter_by(name=self.name, region=self.region, cloud_id=self.cloud_id,
                               volume_attachment_id=volume_attachment.id)
                    .first()
            )

        return (
            db.session.query(self.__class__)
                .filter_by(name=self.name, region=self.region, cloud_id=self.cloud_id,
                           volume_attachment_id=self.volume_attachment_id)
                .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
                (self.name == other.name)
                and (self.zone == other.zone)
                and (self.resource_id == other.resource_id)
                and (self.capacity == other.capacity)
                and (self.encryption == other.encryption)
                and (self.iops == other.iops)
                and (self.status == other.status)
        ):
            return False

        if (self.volume_profile and not other.volume_profile) or (
                not self.volume_profile and other.volume_profile
        ):
            return False

        if self.volume_profile and other.volume_profile:
            if not self.volume_profile.params_eq(other.volume_profile):
                return False

        return True

    def add_update_db(self, volume_attachment=None):
        existing = self.get_existing_from_db(volume_attachment)
        if not existing:
            self.ibm_volume_attachment = volume_attachment
            volume_profile = self.volume_profile
            self.volume_profile = None
            if volume_profile:
                self.volume_profile = volume_profile.add_update_db()
            db.session.add(self)
            db.session.commit()
            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.zone = self.zone
            existing.region = self.region
            existing.resource_id = self.resource_id
            existing.capacity = self.capacity
            existing.encryption = self.encryption
            existing.iops = self.iops
            existing.status = self.status
            db.session.commit()

            volume_profile = self.volume_profile
            self.volume_profile = None

            if volume_profile:
                existing.volume_profile = volume_profile.add_update_db()
            else:
                existing.volume_profile = None
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.CAPACITY_KEY: self.capacity,
            self.IOPS_KEY: self.iops,
            self.ZONE_KEY: self.zone,
            self.ENCRYPTION_KEY: self.encryption,
            self.PROFILE_KEY: self.volume_profile.to_json()
            if self.volume_profile
            else "",
            self.STATUS_KEY: self.status,
            self.ORIGINAL_CAPACITY_KEY: self.original_capacity
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "capacity": self.capacity,
            "profile": self.volume_profile.to_json_body()
            if self.volume_profile
            else "",
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
        # TODO: store ibm status as well and make this status a hybrid property
        status = None
        if json_body["status"] == "pending":
            status = "CREATING"
        elif json_body["status"] == "available":
            status = "CREATED"
        elif json_body["status"] == "pending_deletion":
            status = "DELETING"
        elif json_body["status"] == "failed":
            status = "ERROR_"

        assert status

        ibm_volume = IBMVolume(
            name=json_body["name"], capacity=json_body["capacity"], zone=json_body["zone"]["name"],
            iops=json_body["iops"], encryption=json_body["encryption"], resource_id=json_body["id"], region=region,
            status=status
        )

        return ibm_volume


class IBMVolumeAttachment(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    TYPE = "type"
    IS_DELETE_KEY = "is_delete"
    VOLUME_KEY = "volume"
    IS_MIGRATION_ENABLED_KEY = "is_migration_enabled"
    VOLUME_INDEX_KEY = "volume_index"

    __tablename__ = "ibm_volume_attachments"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    resource_id = Column(String(64))
    type = Column(String(255), nullable=False)
    is_delete = Column(Boolean, default=True, nullable=False)
    volume_index = Column(Integer, nullable=True)
    is_migration_enabled = Column(Boolean, default=True, nullable=False)
    instance_id = Column(String(32), ForeignKey("ibm_instances.id"))

    volume = relationship(
        "IBMVolume",
        backref=backref("ibm_volume_attachment"),
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            name,
            resource_id,
            instance_id,
            type,
            name="uix_ibm_volume_name_resource_id_instance_id_type",
        ),
    )

    def __init__(self, name, type_, is_delete=True, resource_id=None, volume_index=None, is_migration_enabled=False):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.type = type_
        self.is_delete = is_delete
        self.resource_id = resource_id
        self.volume_index = volume_index
        self.is_migration_enabled = is_migration_enabled

    def make_copy(self):
        obj = IBMVolumeAttachment(
            name=self.name,
            type_=self.type,
            is_delete=self.is_delete,
            resource_id=self.resource_id,
            is_migration_enabled=self.is_migration_enabled,
            volume_index=self.volume_index
        )
        if self.volume:
            obj.volume = self.volume.make_copy()

        return obj

    def get_existing_from_db(self, instance=None):
        if instance:
            return (
                db.session.query(self.__class__)
                    .filter_by(name=self.name, instance_id=instance.id)
                    .first()
            )
        return (
            db.session.query(self.__class__)
                .filter_by(name=self.name, instance_id=self.instance_id)
                .first()
        )

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (
                (self.name == other.name)
                and (self.type == other.type)
                and (self.resource_id == other.resource_id)
                and (self.is_delete == other.is_delete)
        ):
            return False

        if (self.volume and not other.volume) or (not self.volume and other.volume):
            return False

        if self.volume and other.volume:
            if not self.volume.params_eq(other.volume):
                return False

        return True

    def add_update_db(self, instance):
        existing = self.get_existing_from_db(instance)
        if not existing:
            volume = self.volume
            self.volume = None
            self.ibm_instance = instance
            db.session.add(self)
            db.session.commit()

            if volume:
                self.volume = volume.add_update_db(self)
                db.session.commit()

            return self

        if not self.params_eq(existing):
            existing.name = self.name
            existing.type = self.type
            existing.resource_id = self.resource_id
            existing.is_delete = self.is_delete
            db.session.commit()

            volume = self.volume
            self.volume = None
            if volume:
                existing.volume = volume.add_update_db(existing)
            else:
                existing.volume = None
            db.session.commit()

        return existing

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.TYPE: self.type,
            self.IS_DELETE_KEY: self.is_delete,
            self.VOLUME_KEY: self.volume.to_json() if self.volume else "",
            self.IS_MIGRATION_ENABLED_KEY: self.is_migration_enabled,
            self.VOLUME_INDEX_KEY: self.volume_index
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "delete_volume_on_instance_delete": self.is_delete,
            "volume": self.volume.to_json_body() if self.volume else "",
        }

    @classmethod
    def from_ibm_json_body(cls, json_body):
        return IBMVolumeAttachment(
            name=json_body["name"], type_=json_body["type"],
            is_delete=json_body.get("delete_volume_on_instance_delete"), resource_id=json_body["id"]
        )
