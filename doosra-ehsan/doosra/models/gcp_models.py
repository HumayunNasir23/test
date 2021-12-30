import uuid
from datetime import datetime

from flask import current_app
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import backref, relationship

from doosra import db
from doosra.common.consts import CREATING, CREATED, SUCCESS, FAILED
from doosra.models.common_models import JSONEncodedDict, MutableDict

gcp_instance_tags = db.Table('gcp_instance_tags',
                             Column('tag_id', String(32), ForeignKey('gcp_tags.id'), nullable=False),
                             Column('instance_id', String(32), ForeignKey('gcp_instances.id'), nullable=False),
                             PrimaryKeyConstraint('tag_id', 'instance_id'))

gcp_firewall_tags = db.Table('gcp_firewall_tags',
                             Column('tag_id', String(32), ForeignKey('gcp_tags.id'), nullable=False),
                             Column('firewall_id', String(32), ForeignKey('gcp_firewall_rules.id'), nullable=False),
                             PrimaryKeyConstraint('tag_id', 'firewall_id'))

gcp_firewall_target_tags = db.Table('gcp_firewall_target_tags',
                                    Column('tag_id', String(32), ForeignKey('gcp_tags.id'), nullable=False),
                                    Column('firewall_id', String(32), ForeignKey('gcp_firewall_rules.id'),
                                           nullable=False),
                                    PrimaryKeyConstraint('tag_id', 'firewall_id'))

gcp_instance_groups_instances = db.Table('gcp_instance_groups_instances',
                                         Column('instance_id', String(32), ForeignKey('gcp_instances.id'),
                                                nullable=False),
                                         Column('instance_group_id', String(32), ForeignKey('gcp_instance_groups.id'),
                                                nullable=False),
                                         PrimaryKeyConstraint('instance_id', 'instance_group_id'))


class GcpCloud(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    LAST_SYNCED_AT = "last_synced_at"
    CLOUD_PROJECT_KEY = "cloud_projects"

    __tablename__ = 'gcp_clouds'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), Enum("VALID", "INVALID"), nullable=False)
    last_synced_at = Column(DateTime)
    project_id = Column(String(32), ForeignKey('projects.id'), nullable=False)

    gcp_credentials = relationship('GCPCredentials', backref='gcp_cloud', cascade="all, delete-orphan",
                                   uselist=False)
    gcp_cloud_projects = relationship('GcpCloudProject', backref='gcp_cloud', cascade="all, delete-orphan",
                                      lazy="dynamic")
    gcp_tasks = relationship('GcpTask', backref='gcp_cloud', cascade="all, delete-orphan", lazy="dynamic")

    def __init__(self, name, project_id, status="INVALID"):
        self.id = self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = status
        self.project_id = project_id

    def make_copy(self):
        cloud_obj = GcpCloud(self.name, self.project_id, self.status)
        for cloud_project in self.gcp_cloud_projects.all():
            cloud_obj.gcp_cloud_projects.append(cloud_project.make_copy())

        return cloud_obj

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.CLOUD_PROJECT_KEY: [cloud_project.to_json() for cloud_project in self.gcp_cloud_projects.all()]
        }


class GCPCredentials(db.Model):
    ID_KEY = "id"
    TOKEN_KEY = "token"
    REFRESH_TOKEN_KEY = "refresh_token"
    TOKEN_URI_KEY = "token_uri"
    CLIENT_ID_KEY = "client_id"
    CLIENT_SECRET_KEY = "client_secret"
    SCOPES_KEY = "scopes"

    __tablename__ = "gcp_credentials"

    id = Column(String(32), primary_key=True)
    token = Column(String(255), nullable=False)
    refresh_token = Column(String(255))
    token_uri = Column(String(255))
    client_id = Column(String(255))
    client_secret = Column(String(255))
    scopes = Column(MutableDict.as_mutable(JSONEncodedDict))
    cloud_id = Column(String(32), ForeignKey('gcp_clouds.id'), nullable=False)

    def __init__(self, credentials):
        self.id = self.id = str(uuid.uuid4().hex)
        self.token = credentials.token
        self.refresh_token = credentials.refresh_token
        self.token_uri = credentials.token_uri
        self.client_id = credentials.client_id
        self.client_secret = credentials.client_secret
        self.scopes = {self.SCOPES_KEY: credentials.scopes}

    def to_json(self):
        return {
            self.TOKEN_KEY: self.token,
            self.REFRESH_TOKEN_KEY: self.refresh_token,
            self.TOKEN_URI_KEY: self.token_uri,
            self.CLIENT_ID_KEY: self.client_id,
            self.CLIENT_SECRET_KEY: self.client_secret,
            self.SCOPES_KEY: self.scopes.get(self.SCOPES_KEY) if self.scopes else None
        }


class GcpTask(db.Model):
    ID_KEY = "id"
    CLOUD_ID_KEY = "cloud_id"
    STATUS_KEY = "status"
    ACTION_KEY = "action"
    TYPE_KEY = "type"
    RESOURCE_ID_KEY = "resource_id"
    RESULT_KEY = "result"
    STARTED_AT_KEY = "started_at"
    MESSAGE_KEY = "message"

    __tablename__ = 'gcp_tasks'

    id = Column(String(100), primary_key=True)
    type = Column(String(32),
                  Enum("CLOUD", "PROJECT", "REGION", "VPC", "INSTANCE", "FIREWALL", "INSTANCE-GROUP", "LOAD-BALANCER"),
                  nullable=False)
    _status = Column(String(32), Enum(CREATED, SUCCESS, FAILED), nullable=False)
    action = Column(String(32), Enum("ADD", "UPDATE", "DELETE", "SYNC"), nullable=False)
    result = Column(MutableDict.as_mutable(JSONEncodedDict), nullable=True)
    resource_id = Column(String(32), nullable=True)
    message = Column(String(500), nullable=True)
    started_at = Column(DateTime, nullable=False)
    last_updated_at = Column(DateTime, onupdate=datetime.utcnow())
    completed_at = Column(DateTime)
    cloud_id = Column(String(32), ForeignKey('gcp_clouds.id'))

    def __init__(self, task_id, type_, action, cloud_id, resource_id=None, message=None):
        self.id = task_id
        self.status = CREATED
        self.started_at = datetime.utcnow()
        self.type = type_
        self.action = action
        self.resource_id = resource_id
        self.message = message
        self.cloud_id = cloud_id

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        if value == SUCCESS or value == FAILED:
            self.completed_at = datetime.utcnow()

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.STATUS_KEY: self.status,
            self.ACTION_KEY: self.action,
            self.TYPE_KEY: self.type,
            self.RESULT_KEY: self.result,
            self.RESOURCE_ID_KEY: self.resource_id,
            self.MESSAGE_KEY: self.message,
            self.CLOUD_ID_KEY: self.cloud_id,
            self.STARTED_AT_KEY: self.started_at
        }


class GcpCloudProject(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    PROJECT_ID_KEY = "project_id"
    VPC_NETWORK_KEY = "vpc_networks"
    LOAD_BALANCERS_KEY = "load_balancers"

    __tablename__ = 'gcp_cloud_projects'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    project_id = Column(String(255))
    cloud_id = Column(String(32), ForeignKey('gcp_clouds.id'), nullable=False)
    user_project_id = Column(String(32), ForeignKey('projects.id'), nullable=False)

    vpc_networks = relationship('GcpVpcNetwork', backref='gcp_cloud_project', cascade="all, delete-orphan",
                                lazy='dynamic')
    addresses = relationship('GcpAddress', backref='gcp_cloud_project', cascade="all, delete-orphan", lazy='dynamic')
    instances = relationship('GcpInstance', backref='gcp_cloud_project', cascade="all, delete-orphan",
                             lazy='dynamic')
    health_checks = relationship('GcpHealthCheck', backref='gcp_cloud_project', cascade="all, delete-orphan",
                                 lazy='dynamic')
    backend_services = relationship('GcpBackendService', backref='gcp_cloud_project', cascade="all, delete-orphan",
                                    lazy='dynamic')
    forwarding_rules = relationship('GcpForwardingRule', backref='gcp_cloud_project', cascade="all, delete-orphan",
                                    lazy='dynamic')
    url_maps = relationship('GcpUrlMap', backref='gcp_cloud_project', cascade="all, delete-orphan",
                            lazy='dynamic')
    load_balancers = relationship('GcpLoadBalancer', backref='gcp_cloud_project', cascade="all, delete-orphan",
                                  lazy='dynamic')

    def __init__(self, name, project_id, cloud_id=None):
        self.id = self.id = str(uuid.uuid4().hex)
        self.name = name
        self.project_id = project_id
        self.cloud_id = cloud_id

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not ((self.name == other.name) and
                (self.project_id == other.project_id)):
            return False

        return True

    def make_copy(self):
        cloud_project_obj = GcpCloudProject(self.name, self.project_id, self.cloud_id)
        for vpc_network in self.vpc_networks.all():
            cloud_project_obj.vpc_networks.append(vpc_network.make_copy())

        return cloud_project_obj

    def add_update_db(self, existing=None):
        if not existing:
            current_app.logger.debug("Adding Cloud project '{}' to database".format(self.name))
            db.session.add(self)
            db.session.commit()
            return

        if not self.params_eq(existing):
            current_app.logger.debug("Updating Cloud '{}' project to database".format(self.name))
            existing.name = self.name
            db.session.commit()

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.PROJECT_ID_KEY: self.project_id,
            self.VPC_NETWORK_KEY: [vpc.to_json() for vpc in self.vpc_networks.all()],
            self.LOAD_BALANCERS_KEY: [load_balancer.to_json() for load_balancer in self.load_balancers.all()]
        }

    def to_json_body(self, update=False):
        if update:
            return {
                "name": self.name}
        return {
            "name": self.name
        }


class GcpVpcNetwork(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    DESCRIPTION_KEY = "description"
    AUTO_CREATE_SUBNETWORKS_KEY = "auto_create_subnetworks"
    ROUTING_MODE_KEY = "routing_mode"
    SUBNET_KEY = "subnets"
    STATUS_KEY = "status"
    NETWORK_INTERFACES_KEY = "network_interfaces"
    TAGS_KEY = "network_tags"
    FIREWALL_KEY = "firewall_rules"
    INSTANCE_GROUPS_KEY = "instance_groups"

    __tablename__ = 'gcp_vpc_networks'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    auto_create_subnetworks = Column(Boolean, default=False)
    routing_mode = Column(String(255), Enum("GLOBAL", "REGIONAL"), default="REGIONAL", nullable=False)
    status = Column(String(50), nullable=False)
    cloud_project_id = Column(String(32), ForeignKey('gcp_cloud_projects.id'), nullable=False)

    subnets = relationship('GcpSubnet', backref='gcp_vpc_network', cascade="all, delete-orphan", lazy="dynamic")
    tags = relationship('GcpTag', backref='gcp_vpc_network', cascade="all, delete-orphan", lazy="dynamic")
    network_interfaces = relationship('GcpNetworkInterface', backref='gcp_vpc_network', cascade="all, delete-orphan",
                                      lazy="dynamic")
    firewall_rules = relationship('GcpFirewallRule', backref='gcp_vpc_network', cascade="all, delete-orphan",
                                  lazy="dynamic")
    instance_groups = relationship('GcpInstanceGroup', backref='gcp_vpc_network', cascade="all, delete-orphan",
                                   lazy="dynamic")

    def __init__(self, name, description=None, auto_create_subnetworks=False, routing_mode="REGIONAL",
                 cloud_project_id=None):
        self.id = self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = CREATING
        self.description = description
        self.auto_create_subnetworks = auto_create_subnetworks
        self.routing_mode = routing_mode
        self.cloud_project_id = cloud_project_id

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not ((self.name == other.name) and
                (self.description == other.description) and
                (self.auto_create_subnetworks == other.auto_create_subnetworks) and
                (self.routing_mode == other.routing_mode)):
            return False

        if not len(self.subnets.all()) == len(other.subnets.all()):
            return False

        for subnet in self.subnets.all():
            found = False
            for subnet_ in other.subnets.all():
                if subnet.name == subnet_.name:
                    found = True

            if not found:
                return False

        return True

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.DESCRIPTION_KEY: self.description,
            self.AUTO_CREATE_SUBNETWORKS_KEY: self.auto_create_subnetworks,
            self.SUBNET_KEY: [subnet.to_json() for subnet in self.subnets.all()],
            self.TAGS_KEY: [tag.to_json() for tag in self.tags.all()],
            self.NETWORK_INTERFACES_KEY: [interface.to_json() for interface in self.network_interfaces.all()],
            self.INSTANCE_GROUPS_KEY: [instance.to_json() for instance in self.instance_groups.all()],
            self.FIREWALL_KEY: [firewall_rule.to_json() for firewall_rule in self.firewall_rules.all()]
        }

    def to_json_body(self, update=False):
        if update:
            return {
                "routingMode": {"routingConfig": self.routing_mode}
            }
        return {
            "name": self.name,
            "description": self.description,
            "autoCreateSubnetworks": self.auto_create_subnetworks,
            "routingMode": {"routingConfig": self.routing_mode},
        }

    def make_copy(self):
        vpc_obj = GcpVpcNetwork(self.name, self.description, self.auto_create_subnetworks, self.routing_mode,
                                self.cloud_project_id)
        for subnet in self.subnets.all():
            vpc_obj.subnets.append(subnet.make_copy())

        return vpc_obj

    def add_update_db(self, existing=None):
        if not existing:
            current_app.logger.debug("Adding VPC '{}' network to database".format(self.name))
            db.session.add(self)
            db.session.commit()
            return

        if not self.params_eq(existing):
            current_app.logger.debug("Updating VPC network '{}' to database".format(self.name))
            existing.description = self.description
            existing.auto_create_subnetworks = self.auto_create_subnetworks
            existing.routing_mode = self.routing_mode
            db.session.commit()

            for subnet in existing.subnets.all():
                found = False
                for subnet_ in self.subnets.all():
                    if subnet.name == subnet_.name:
                        found = True
                        break

                if not found:
                    db.session.remove(subnet)
                    db.session.commit()

            for subnet in self.subnets.all():
                existing_subnet = db.session.query(GcpSubnet).filter_by(
                    name=subnet.name, region=subnet.region, vpc_network_id=existing.id).first()
                subnet.add_update_db(existing_subnet)


class GcpSubnet(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    DESCRIPTION_KEY = "description"
    IP_CIDR_RANGE_KEY = "ip_cidr_range"
    REGION_KEY = "region"
    ENABLE_FLOW_LOGS_KEY = "enable_flow_logs"
    PRIVATE_GOOGLE_ACCESS_KEY = "private_google_access"
    NETWORK_KEY = "network"
    SECONDARY_IP_RANGE_KEY = "secondary_ip_ranges"
    STATUS_KEY = "status"

    __tablename__ = 'gcp_subnets'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    ip_cidr_range = Column(String(255), nullable=False)
    region = Column(String(255), nullable=False)
    enable_flow_logs = Column(Boolean, nullable=False, default=False)
    private_google_access = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False)
    vpc_network_id = Column(String(32), ForeignKey('gcp_vpc_networks.id'), nullable=False)

    secondary_ip_ranges = relationship('GcpSecondaryIpRange', backref='gcp_subnet', cascade="all, delete-orphan",
                                       lazy="dynamic")
    network_interfaces = relationship('GcpNetworkInterface', backref='gcp_subnet', cascade="all, delete-orphan",
                                      lazy="dynamic")

    def __init__(self, name, ip_cidr_range, region, enable_flow_logs=False, private_google_access=False,
                 description=None, vpc_network_id=None):
        self.id = self.id = str(uuid.uuid4().hex)
        self.name = name
        self.description = description
        self.ip_cidr_range = ip_cidr_range
        self.region = region
        self.enable_flow_logs = enable_flow_logs
        self.private_google_access = private_google_access
        self.vpc_network_id = vpc_network_id
        self.status = CREATING

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not ((self.name == other.name) and
                (self.description == other.description) and
                (self.ip_cidr_range == other.ip_cidr_range) and
                (self.region == other.region) and
                (self.enable_flow_logs == other.enable_flow_logs) and
                (self.private_google_access == other.private_google_access)):
            return False

        if not len(self.secondary_ip_ranges.all()) == len(other.secondary_ip_ranges.all()):
            return False

        for ip_range in self.secondary_ip_ranges.all():
            found = False
            for ip_range_ in other.secondary_ip_ranges.all():
                if ip_range.name == ip_range_.name:
                    found = True

            if not found:
                return False

        return True

    def add_update_db(self, existing=None):
        if not existing:
            current_app.logger.debug("Adding '{}' subnet to database".format(self.name))
            subnet_to_add = self.make_copy()
            db.session.add(subnet_to_add)
            db.session.commit()
            return

        if not self.params_eq(existing):
            current_app.logger.debug("Updating '{}' subnet to database".format(self.name))
            existing.name = self.name
            existing.description = self.description
            existing.ip_cidr_range = self.ip_cidr_range
            existing.region = self.region
            existing.enable_flow_logs = self.enable_flow_logs
            existing.private_google_access = self.private_google_access
            db.session.commit()

            for ip_range in existing.secondary_ip_ranges.all():
                found = False
                for ip_range_ in self.secondary_ip_ranges.all():
                    if ip_range.name == ip_range_.name:
                        found = True
                        break

                if not found:
                    db.session.remove(ip_range)
                    db.session.commit()

            for ip_range in self.secondary_ip_ranges.all():
                existing_ip_range = db.session.query(GcpSecondaryIpRange).filter_by(
                    name=ip_range.name, subnet_id=self.id).first()
                ip_range.add_update_db(existing_ip_range)

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.DESCRIPTION_KEY: self.description,
            self.IP_CIDR_RANGE_KEY: self.ip_cidr_range,
            self.REGION_KEY: self.region,
            self.ENABLE_FLOW_LOGS_KEY: self.enable_flow_logs,
            self.PRIVATE_GOOGLE_ACCESS_KEY: self.private_google_access,
            self.STATUS_KEY: self.status,
            self.SECONDARY_IP_RANGE_KEY: [ip_range.to_json() for ip_range in self.secondary_ip_ranges.all()]
        }

    def to_json_body(self, update=False):
        if update:
            return {
                "ipCidrRange": self.ip_cidr_range,
                "enableFlowLogs": self.enable_flow_logs,
                "privateIpGoogleAccess": self.private_google_access
            }
        return {
            "name": self.name,
            "description": self.description,
            "ipCidrRange": self.ip_cidr_range,
            "enableFlowLogs": self.enable_flow_logs,
            "privateIpGoogleAccess": self.private_google_access,
            "region": "projects/{project}/regions/{region}".format(
                region=self.region, project=self.gcp_vpc_network.gcp_cloud_project.project_id),
            "network": "projects/{project}/global/networks/{network}".format(
                network=self.gcp_vpc_network.name, project=self.gcp_vpc_network.gcp_cloud_project.project_id),
            "secondaryIpRanges": [ip_range.to_json_body() for ip_range in self.secondary_ip_ranges.all()]
        }

    def make_copy(self):
        subnet_obj = GcpSubnet(self.name, self.ip_cidr_range, self.region, self.enable_flow_logs,
                               self.private_google_access, self.description, self.vpc_network_id)
        for ip_range in self.secondary_ip_ranges.all():
            subnet_obj.secondary_ip_ranges.append(ip_range.make_copy())

        return subnet_obj


class GcpSecondaryIpRange(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    IP_CIDR_RANGE_KEY = "ip_cidr_range"

    __tablename__ = 'gcp_secondary_ip_ranges'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    ip_cidr_range = Column(String(255), nullable=False)

    subnet_id = Column(String(32), ForeignKey('gcp_subnets.id'), nullable=False)

    def __init__(self, name, ip_cidr_range, subnet_id=None):
        self.id = self.id = str(uuid.uuid4().hex)
        self.name = name
        self.ip_cidr_range = ip_cidr_range
        self.subnet_id = subnet_id

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not ((self.name == other.name) and
                (self.ip_cidr_range == other.ip_cidr_range)):
            return False

        return True

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.IP_CIDR_RANGE_KEY: self.ip_cidr_range
        }

    def to_json_body(self, update=False):
        if update:
            return {
                "rangeName": self.name,
                "ipCidrRange": self.ip_cidr_range
            }
        return {
            "rangeName": self.name,
            "ipCidrRange": self.ip_cidr_range
        }

    def make_copy(self):
        return GcpSecondaryIpRange(name=self.name, ip_cidr_range=self.ip_cidr_range, subnet_id=self.subnet_id)

    def add_update_db(self, existing=None):
        if not existing:
            current_app.logger.debug("Adding Secondary IP range '{}' to DB".format(self.name))
            db.session.add(self)
            db.session.commit()
            return

        if not self.params_eq(existing):
            current_app.logger.debug("Updating Secondary IP range '{}' to DB".format(self.name))
            existing.ip_cidr_range = self.ip_cidr_range


class GcpFirewallRule(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    DESCRIPTION_KEY = "description"
    PRIORITY_KEY = "priority"
    DIRECTION_KEY = "direction"
    ACTION_KEY = "action"
    TARGET_TAGS_KEY = "target_tags"
    IP_RANGE_KEY = "ip_ranges"
    IP_PROTOCOL_KEY = "ip_protocols"
    TAGS_KEY = "tags"
    STATUS_KEY = "status"

    __tablename__ = 'gcp_firewall_rules'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    priority = Column(Integer, nullable=False, default=1000)
    direction = Column(String(255), Enum('INGRESS', 'EGRESS'), nullable=False)
    action = Column(String(255), Enum('ALLOW', 'DENY'), nullable=False)
    ip_ranges = Column(MutableDict.as_mutable(JSONEncodedDict))
    status = Column(String(50), nullable=False)
    vpc_network_id = Column(String(32), ForeignKey('gcp_vpc_networks.id'))

    ip_protocols = relationship("GcpIpProtocol", backref='gcp_firewall_rules', cascade="all, delete-orphan",
                                lazy="dynamic")
    tags = relationship('GcpTag', secondary=gcp_firewall_tags, backref=backref('gcp_tag_firewall_rules'),
                        lazy='dynamic')
    target_tags = relationship('GcpTag', secondary=gcp_firewall_target_tags,
                               backref=backref('gcp_target_tag_firewall_rules'), lazy='dynamic')

    def __init__(self, name, direction, action, priority=1000, description=None, ip_ranges=None, vpc_network_id=None):
        self.id = self.id = str(uuid.uuid4().hex)
        self.name = name
        self.description = description
        self.action = action
        self.status = CREATING
        self.priority = priority
        self.direction = direction
        self.ip_ranges = {self.IP_RANGE_KEY: ip_ranges}
        self.vpc_network_id = vpc_network_id

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.DESCRIPTION_KEY: self.description,
            self.ACTION_KEY: self.action,
            self.PRIORITY_KEY: self.priority,
            self.DIRECTION_KEY: self.direction,
            self.IP_RANGE_KEY: self.ip_ranges.get(self.IP_RANGE_KEY),
            self.IP_PROTOCOL_KEY: [protocol.to_json() for protocol in self.ip_protocols.all()],
            self.TARGET_TAGS_KEY: [tag.to_json() for tag in self.target_tags.all()],
            self.TAGS_KEY: [tag.to_json() for tag in self.tags.all()]
        }

    def to_json_body(self):
        json_body = {
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "direction": self.direction,
            "network": "global/networks/{network}".format(network=self.gcp_vpc_network.name)
        }

        if self.target_tags:
            json_body["targetTags"] = [tag.tag for tag in self.target_tags.all()]

        if self.direction == "INGRESS":
            json_body["sourceRanges"] = self.ip_ranges.get(self.IP_RANGE_KEY)
            json_body["sourceTags"] = [tag.tag for tag in self.tags.all()]
        elif self.direction == "EGRESS":
            json_body["destinationRanges"] = self.ip_ranges.get(self.IP_RANGE_KEY)

        if self.action == "ALLOW":
            json_body["allowed"] = [ip_protocol.to_json_body() for ip_protocol in self.ip_protocols.all()]
        elif self.action == "DENY":
            json_body["denied"] = [ip_protocol.to_json_body() for ip_protocol in self.ip_protocols.all()]

        return json_body

    def make_copy(self):
        firewall_rule_obj = GcpFirewallRule(self.name, self.direction, self.action, self.priority, self.description,
                                            self.ip_ranges.get(self.IP_RANGE_KEY), self.vpc_network_id)
        for ip_protocol in self.ip_protocols.all():
            firewall_rule_obj.ip_protocols.append(ip_protocol.make_copy())
        return firewall_rule_obj


class GcpAddress(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    TYPE_KEY = "type"
    STATUS_KEY = "status"
    DESCRIPTION_KEY = "description"
    IP_VERSION_KEY = "ip_version"
    REGION_KEY = "region"
    ADDRESS_KEY = "address"

    __tablename__ = 'gcp_addresses'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    region = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    type = Column(String(255), Enum('INTERNAL', 'EXTERNAL'), default='EXTERNAL', nullable=False)
    description = Column(String(1024))
    ip_version = Column(String(255), Enum("IPV4", "IPV6"), nullable=True)

    cloud_project_id = Column(String(32), ForeignKey('gcp_cloud_projects.id'), nullable=False)
    network_interfaces = relationship('GcpNetworkInterface', backref='gcp_address', cascade="all, delete-orphan",
                                      lazy="dynamic")

    def __init__(self, name, type_=None, region=None, address=None, ip_version=None, description=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = CREATING
        self.description = description
        self.type = type_ or 'EXTERNAL'
        self.ip_version = ip_version or 'IPV4'
        self.region = region
        self.address = address

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.TYPE_KEY: self.type,
            self.ADDRESS_KEY: self.address,
            self.DESCRIPTION_KEY: self.description,
            self.IP_VERSION_KEY: self.ip_version,
            self.REGION_KEY: self.region
        }

    def to_json_body(self):
        json_data = {
            "name": self.name,
            "description": self.description,
            "addressType": self.type
        }
        if self.region:
            json_data['region'] = self.region
        else:
            json_data["ipVersion"] = self.ip_version

        if self.address:
            json_data['address'] = self.address
        return json_data


class GcpInstance(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    DESCRIPTION_KEY = "description"
    ZONE_KEY = "zone"
    MACHINE_TYPE = "machine_type"
    INTERFACES_KEY = "interfaces"
    DISKS_KEY = "disks"
    STATUS_KEY = "status"
    NETWORK_TAGS_KEY = "network_tags"

    __tablename__ = 'gcp_instances'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    description = Column(String(1024))
    zone = Column(String(255), nullable=False)
    machine_type = Column(String(255), nullable=False)

    cloud_project_id = Column(String(32), ForeignKey('gcp_cloud_projects.id'), nullable=False)

    interfaces = relationship('GcpNetworkInterface', backref='gcp_instance', cascade="all, delete-orphan",
                              lazy="dynamic")
    disks = relationship("GcpDisk", secondary="instance_disks")
    tags = relationship('GcpTag', secondary=gcp_instance_tags, backref=backref('gcp_instances'), lazy='dynamic')

    def __init__(self, name, zone, machine_type, cloud_project_id=None, description=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = CREATING
        self.description = description
        self.zone = zone
        self.machine_type = machine_type
        self.cloud_project_id = cloud_project_id

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (self.name == other.name):
            return False

        return True

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.DESCRIPTION_KEY: self.description,
            self.ZONE_KEY: self.zone,
            self.MACHINE_TYPE: self.machine_type,
            self.DISKS_KEY: [disk.to_json() for disk in self.disks],
            self.NETWORK_TAGS_KEY: [tag.to_json() for tag in self.tags.all()]
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "zone": self.zone,
            "description": self.description,
            "tags": {"items": [tag.tag for tag in self.tags.all()]},
            "machineType": "projects/{project}/zones/{zone}/machineTypes/{machine}".format(
                project=self.gcp_cloud_project.project_id, zone=self.zone, machine=self.machine_type),
            "networkInterfaces": [interface.to_json_body() for interface in self.interfaces],
            "disks": [disk.to_json_body() for disk in self.disks]
        }

    def make_copy(self):
        gcp_instance = GcpInstance(name=self.name, zone=self.zone, machine_type=self.machine_type,
                                   description=self.description, cloud_project_id=self.cloud_project_id)
        for interface in self.interfaces:
            gcp_instance.interfaces.append(interface.make_copy())

        for disk in self.disks:
            gcp_instance.disks.append(disk.make_copy())

        return gcp_instance


class GcpDisk(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    TYPE_KEY = "type"
    SIZE_KEY = "size"
    ZONE_KEY = "zone"
    SOURCE_IMAGE_KEY = "source_image"

    __tablename__ = 'gcp_disks'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    disk_type = Column(String(255), nullable=False)
    disk_size = Column(String(255), nullable=False)
    zone = Column(String(255), nullable=False)
    physical_block_size_bytes = Column(String(255))
    source_image = Column(String(255))
    source_snapshot = Column(String(255))

    instance = relationship("GcpInstance", secondary="instance_disks", uselist=False)

    def __init__(self, name, disk_type, disk_size, zone, source_image=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.disk_type = disk_type
        self.disk_size = disk_size
        self.zone = zone
        self.source_image = source_image

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (self.name == other.name):
            return False

        return True

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.ZONE_KEY: self.zone,
            self.TYPE_KEY: self.disk_type,
            self.SIZE_KEY: self.disk_size,
            self.SOURCE_IMAGE_KEY: self.source_image
        }

    def to_json_body(self):
        json_body = {
            "deviceName": self.name,
            "boot": self.instance_disk.boot,
            "mode": self.instance_disk.mode,
            "autoDelete": self.instance_disk.auto_delete,
            "initializeParams": {
                "diskType": "projects/{project}/zones/{zone}/diskTypes/{type}".format(
                    project=self.instance.gcp_cloud_project.project_id, zone=self.zone, type=self.disk_type),
                "diskSizeGb": self.disk_size
            }
        }

        if self.source_image:
            json_body["initializeParams"]["sourceImage"] = self.source_image

        return json_body

    def make_copy(self):
        gcp_disk = GcpDisk(name=self.name, disk_type=self.disk_type, disk_size=self.disk_size,
                           source_image=self.source_image, zone=self.zone)

        if gcp_disk.instance_disk:
            gcp_disk.instance_disk.boot = self.instance_disk.boot
            gcp_disk.instance_disk.mode = self.instance_disk.mode
            gcp_disk.instance_disk.auto_delete = self.instance_disk.auto_delete

        return gcp_disk


class GcpNetworkInterface(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    NETWORK_KEY = "network"
    SUB_NETWORK_KEY = "sub_network"
    INTERNAL_IP_KEY = "primary_internal_ip"
    EXTERNAL_IP_KEY = "external_ip"
    INSTANCE_KEY = "instance"

    __tablename__ = 'gcp_network_interfaces'

    id = Column(String(32), primary_key=True)
    name = Column(String(255))
    primary_internal_ip = Column(String(255))
    alias_ip_ranges = Column(String(255))
    external_ip = Column(String(255))

    instance_id = Column(String(32), ForeignKey('gcp_instances.id'), nullable=False)
    vpc_network_id = Column(String(32), ForeignKey('gcp_vpc_networks.id'), nullable=False)
    sub_network_id = Column(String(32), ForeignKey('gcp_subnets.id'), nullable=False)
    address_id = Column(String(32), ForeignKey('gcp_addresses.id'))

    def __init__(self, name, primary_internal_ip=None, external_ip=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.primary_internal_ip = primary_internal_ip
        self.external_ip = external_ip or 'EPHEMERAL'

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not (self.name == other.name):
            return False

        return True

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.NETWORK_KEY: self.gcp_vpc_network.name if self.gcp_vpc_network else None,
            self.SUB_NETWORK_KEY: self.gcp_subnet.name if self.gcp_subnet else None,
            self.INTERNAL_IP_KEY: self.primary_internal_ip,
            self.EXTERNAL_IP_KEY: self.external_ip,
            self.INSTANCE_KEY: self.gcp_instance.to_json() if self.gcp_instance else None
        }

    def to_json_body(self):
        json_body = {"aliasIpRanges": []}
        if self.gcp_vpc_network:
            json_body["network"] = "projects/{project}/global/networks/{network}".format(
                network=self.gcp_vpc_network.name, project=self.gcp_vpc_network.gcp_cloud_project.project_id)

        if self.gcp_subnet:
            json_body["subnetwork"] = "projects/{project}/regions/{region}/subnetworks/{subnet}".format(
                subnet=self.gcp_subnet.name, project=self.gcp_subnet.gcp_vpc_network.gcp_cloud_project.project_id,
                region=self.gcp_subnet.region)

        if self.primary_internal_ip:
            json_body["networkIP"] = self.primary_internal_ip

        if self.external_ip == 'EPHEMERAL':
            json_body["accessConfigs"] = [{
                "name": "External NAT",
                "type": "ONE_TO_ONE_NAT",
                "networkTier": "PREMIUM"
            }]

        elif self.external_ip == "STATIC":
            json_body["accessConfigs"] = [{
                "name": "External NAT",
                "type": "ONE_TO_ONE_NAT",
                "networkTier": "PREMIUM",
                "natIP": "{}".format(self.gcp_address.address),
            }]

        return json_body

    def make_copy(self):
        return GcpNetworkInterface(name=self.name, primary_internal_ip=self.primary_internal_ip,
                                   external_ip=self.external_ip)


class InstanceDisk(db.Model):
    __tablename__ = 'instance_disks'

    id = Column(Integer, primary_key=True)
    boot = Column(Boolean, default=False)
    auto_delete = Column(Boolean, default=False)
    mode = Column(String(255))
    instance_id = Column(String(32), ForeignKey('gcp_instances.id'))
    disk_id = Column(String(32), ForeignKey('gcp_disks.id'))

    instance = relationship(GcpInstance, backref=backref("instance_disks", cascade="all, delete-orphan"))
    disk = relationship(GcpDisk, backref=backref("instance_disk", cascade="all, delete-orphan", uselist=False))


class GcpTag(db.Model):
    ID_KEY = "id"
    TAG_KEY = "tag"

    __tablename__ = 'gcp_tags'

    id = Column(String(32), primary_key=True)
    tag = Column(String(255), nullable=False)
    vpc_network_id = Column(String(32), ForeignKey('gcp_vpc_networks.id'))

    def __init__(self, tag, vpc_network_id=None):
        self.id = str(uuid.uuid4().hex)
        self.tag = tag
        self.vpc_network_id = vpc_network_id

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.TAG_KEY: self.tag
        }


class GcpInstanceGroup(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    DESCRIPTION_KEY = "description"
    ZONE_KEY = "zone"
    NETWORK_KEY = "network"
    SUBNETWORK_KEY = "subnetwork"
    INSTANCES_KEY = "instances"

    __tablename__ = 'gcp_instance_groups'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    description = Column(String(1024))
    zone = Column(String(255), nullable=False)

    vpc_network_id = Column(String(32), ForeignKey('gcp_vpc_networks.id'), nullable=False)
    backend_id = Column(String(32), ForeignKey('gcp_backends.id'))

    instances = relationship('GcpInstance', secondary=gcp_instance_groups_instances,
                             backref=backref('gcp_instance_groups'), lazy="dynamic")

    def __init__(self, name, zone, description=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = CREATING
        self.description = description
        self.zone = zone

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.DESCRIPTION_KEY: self.description,
            self.ZONE_KEY: self.zone,
            self.INSTANCES_KEY: [instance.to_json() for instance in self.instances.all()],
        }

    def to_json_body(self):
        json_data = {
            "name": self.name,
            "description": self.description,
            "network": "projects/{project}/global/networks/{network}".format(
                project=self.gcp_vpc_network.gcp_cloud_project.project_id, network=self.gcp_vpc_network.name),
        }
        if self.instances.all():
            instances_list = list()
            for instance in self.instances.all():
                instances_list.append({"instance": "projects/{project}/zones/{zone}/instances/{instance}".format(
                    project=self.gcp_vpc_network.gcp_cloud_project.project_id, zone=self.zone, instance=instance.name)})
            json_data["instances"] = instances_list
        return json_data


class GcpLoadBalancer(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    BACKEND_SERVICES_KEY = "backend_services"
    FORWARDING_RULES_KEY = "forwarding_rules"
    URL_MAP_KEY = "url_map"

    __tablename__ = 'gcp_load_balancers'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    cloud_project_id = Column(String(32), ForeignKey('gcp_cloud_projects.id'), nullable=False)

    backend_services = relationship('GcpBackendService', backref='gcp_load_balancer', cascade="all, delete-orphan",
                                    lazy='dynamic')
    forwarding_rules = relationship('GcpForwardingRule', backref='gcp_load_balancer', cascade="all, delete-orphan",
                                    lazy='dynamic')
    url_map = relationship('GcpUrlMap', backref='gcp_load_balancer', cascade="all, delete-orphan", uselist=False)

    def __init__(self, name):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = CREATING

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.BACKEND_SERVICES_KEY: [backend.to_json() for backend in self.backend_services.all()],
            self.FORWARDING_RULES_KEY: [forwarding_rule.to_json() for forwarding_rule in self.forwarding_rules.all()],
            self.URL_MAP_KEY: self.url_map.to_json() if self.url_map else None
        }


class GcpBackendService(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    DESCRIPTION_KEY = "description"
    PROTOCOL_KEY = "protocol"
    PORT_KEY = "port"
    PORT_NAME_KEY = "port_name"
    TIMEOUT_KEY = "timeout"
    BACKEND_KEY = "backend"
    ENABLE_CDN_KEY = "enable_cdn"
    HEALTH_CHECK_KEY = "health_check"

    __tablename__ = 'gcp_backend_services'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    description = Column(String(1024))
    protocol = Column(String(255))
    port = Column(String(255))
    port_name = Column(String(255))
    timeout = Column(String(255), default="30")
    enable_cdn = Column(Boolean, default=False)

    cloud_project_id = Column(String(32), ForeignKey('gcp_cloud_projects.id'), nullable=False)
    url_map_id = Column(String(32), ForeignKey('gcp_url_maps.id'))
    path_matcher_id = Column(String(32), ForeignKey('gcp_path_matchers.id'))
    path_rule_id = Column(String(32), ForeignKey('gcp_path_rules.id'))
    load_balancer_id = Column(String(32), ForeignKey('gcp_load_balancers.id'))

    backends = relationship('GcpBackend', backref='gcp_backend_service', cascade="all, delete-orphan", lazy='dynamic')
    health_check = relationship('GcpHealthCheck', backref='gcp_backend_service', cascade="all, delete-orphan",
                                uselist=False)

    def __init__(self, name, protocol, port_name, port, timeout="30", description=None, enable_cdn=False):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = CREATING
        self.description = description
        self.timeout = timeout
        self.protocol = protocol
        self.port_name = port_name.lower() if port_name else "http"
        self.port = port or "80"
        self.enable_cdn = enable_cdn

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.DESCRIPTION_KEY: self.description,
            self.PORT_KEY: self.port,
            self.PROTOCOL_KEY: self.protocol,
            self.PORT_NAME_KEY: self.port_name,
            self.TIMEOUT_KEY: self.timeout,
            self.BACKEND_KEY: [backend.to_json() for backend in self.backends.all()],
            self.HEALTH_CHECK_KEY: self.health_check.to_json() if self.health_check else None,
            self.ENABLE_CDN_KEY: self.enable_cdn
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "description": self.description,
            "backends": [backend.to_json_body() for backend in self.backends.all()],
            "healthChecks": ["projects/{project}/global/healthChecks/{health_check}".format(
                project=self.gcp_cloud_project.project_id, health_check=self.health_check.name)],
            "timeoutSec": self.timeout,
            "port": self.port,
            "protocol": self.protocol,
            "portName": self.port_name,
            "enableCDN": self.enable_cdn
        }


class GcpBackend(db.Model):
    ID_KEY = "id"
    DESCRIPTION_KEY = "description"
    INSTANCE_GROUP_KEY = "instance_group"
    MAXIMUM_CPU_UTILIZATION_KEY = "maximum_cpu_utilization"
    CAPACITY_SCALER_KEY = "capacity_scaler"

    __tablename__ = 'gcp_backends'

    id = Column(String(32), primary_key=True)
    description = Column(String(1024))
    max_cpu_utilization = Column(String(255), default="0.8")
    capacity_scaler = Column(String(255), default="1")
    backend_service_id = Column(String(32), ForeignKey('gcp_backend_services.id'), nullable=False)

    instance_group = relationship('GcpInstanceGroup', backref=backref('gcp_backend'), uselist=False)

    def __init__(self, max_cpu_utilization, capacity_scaler, description=None):
        self.id = str(uuid.uuid4().hex)
        self.max_cpu_utilization = max_cpu_utilization
        self.capacity_scaler = capacity_scaler
        self.description = description

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.DESCRIPTION_KEY: self.description,
            self.CAPACITY_SCALER_KEY: self.capacity_scaler,
            self.MAXIMUM_CPU_UTILIZATION_KEY: self.max_cpu_utilization,
            self.INSTANCE_GROUP_KEY: self.instance_group.to_json() if self.instance_group else None
        }

    def to_json_body(self):
        return {
            "description": self.description,
            "group": "projects/{project}/zones/{zone}/instanceGroups/{instance_group}".format(
                project=self.gcp_backend_service.gcp_cloud_project.project_id,
                zone=self.instance_group.zone,
                instance_group=self.instance_group.name),
            "capacityScaler": self.capacity_scaler,
            "maxUtilization": self.max_cpu_utilization
        }


class GcpHealthCheck(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    DESCRIPTION_KEY = "description"
    TYPE_KEY = "type"
    HEALTHY_THRESHOLD_KEY = "healthy_threshold"
    UNHEALTHY_THRESHOLD_KEY = "unhealthy_threshold"
    TIMEOUT_KEY = "timeout"
    CHECK_INTERVAL_KEY = "check_interval"
    PORT_HEALTH_CHECK_KEY = "port_health_check"

    __tablename__ = 'gcp_health_checks'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    description = Column(String(1024))
    type = Column(String(255), nullable=False)
    healthy_threshold = Column(Integer, default=2)
    unhealthy_threshold = Column(Integer, default=3)
    timeout = Column(Integer, default=5)
    check_interval = Column(Integer, default=10)

    cloud_project_id = Column(String(32), ForeignKey('gcp_cloud_projects.id'), nullable=False)
    backend_service_id = Column(String(32), ForeignKey('gcp_backend_services.id'))

    port_health_check = relationship('GcpPortHealthCheck', backref='gcp_health_check', cascade="all, delete-orphan",
                                     uselist=False)

    def __init__(self, name, type_, description=None, healthy_threshold=2, unhealthy_threshold=3, timeout=5,
                 check_interval=10):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.type = type_ or "TCP"
        self.status = CREATING
        self.healthy_threshold = healthy_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.timeout = timeout
        self.description = description
        self.check_interval = check_interval

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.TYPE_KEY: self.type,
            self.DESCRIPTION_KEY: self.description,
            self.HEALTHY_THRESHOLD_KEY: self.healthy_threshold,
            self.UNHEALTHY_THRESHOLD_KEY: self.unhealthy_threshold,
            self.TIMEOUT_KEY: self.timeout,
            self.CHECK_INTERVAL_KEY: self.check_interval,
            self.PORT_HEALTH_CHECK_KEY: self.port_health_check.to_json() if self.port_health_check else None
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "healthyThreshold": self.healthy_threshold,
            "unhealthyThreshold": self.unhealthy_threshold,
            "timeoutSec": self.timeout,
            "checkIntervalSec": self.check_interval,
            "{}HealthCheck".format(
                self.type.lower()): self.port_health_check.to_json_body() if self.port_health_check else None
        }


class GcpPortHealthCheck(db.Model):
    ID_KEY = "id"
    PORT_KEY = "port"
    PROXY_HEADER_KEY = "proxy_header"
    REQUEST_KEY = "request"
    RESPONSE_KEY = "response"

    __tablename__ = 'gcp_port_health_checks'

    id = Column(String(32), primary_key=True)
    port = Column(String(255), nullable=False)
    request = Column(String(255))
    response = Column(String(255))
    proxy_header = Column(String(255))

    health_check_id = Column(String(32), ForeignKey('gcp_health_checks.id'), nullable=False)

    def __init__(self, port, request=None, response=None, proxy_header=None):
        self.id = str(uuid.uuid4().hex)
        self.port = port
        self.request = request
        self.response = response
        self.proxy_header = proxy_header

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.PORT_KEY: self.port,
            self.REQUEST_KEY: self.request,
            self.RESPONSE_KEY: self.response,
            self.PROXY_HEADER_KEY: self.proxy_header
        }

    def to_json_body(self):
        return {
            "port": self.port,
            "request": self.request,
            "response": self.response,
            "proxyHeader": self.proxy_header
        }


class GcpForwardingRule(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    DESCRIPTION_KEY = "description"
    IP_ADDRESS_KEY = "ip_address"
    TYPE_KEY = "type"
    IP_VERSION_KEY = "ip_version"
    IP_PROTOCOL_KEY = "ip_protocol"
    PORT_RANGE_KEY = "port_range"
    TARGET_KEY = "target"
    STATUS_KEY = "status"
    LOAD_BALANCING_SCHEME_KEY = "load_balancing_scheme"
    TARGET_PROXY_KEY = "target_proxy"

    __tablename__ = 'gcp_forwarding_rules'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    ip_version = Column(String(50), Enum('IPV4', 'IPV6'), nullable=False)
    type = Column(String(50), Enum('GLOBAL'), default="GLOBAL", nullable=False)
    description = Column(String(1024))
    ip_address = Column(String(255))
    ip_protocol = Column(String(255), nullable=False)
    port_range = Column(String(255))
    load_balancing_scheme = Column(String(255), nullable=False)

    cloud_project_id = Column(String(32), ForeignKey('gcp_cloud_projects.id'), nullable=False)
    load_balancer_id = Column(String(32), ForeignKey('gcp_load_balancers.id'))

    target_proxy = relationship('GcpTargetProxy', backref='gcp_forwarding_rule', cascade="all, delete-orphan",
                                uselist=False)

    def __init__(self, name, ip_address, ip_protocol, ip_version='IPV4', port_range=None, description=None,
                 load_balancing_scheme="EXTERNAL", type_="GLOBAL"):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = CREATING
        self.description = description
        self.ip_address = ip_address
        self.ip_version = ip_version
        self.ip_protocol = ip_protocol or "HTTP"
        self.port_range = port_range
        self.type = type_
        self.load_balancing_scheme = load_balancing_scheme

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.TYPE_KEY: self.type,
            self.DESCRIPTION_KEY: self.description,
            self.IP_ADDRESS_KEY: self.ip_address,
            self.IP_PROTOCOL_KEY: self.ip_protocol,
            self.IP_VERSION_KEY: self.ip_version,
            self.PORT_RANGE_KEY: self.port_range,
            self.LOAD_BALANCING_SCHEME_KEY: self.load_balancing_scheme,
            self.TARGET_PROXY_KEY: self.target_proxy.to_json() if self.target_proxy else None
        }

    def to_json_body(self):
        json_data = {
            "name": self.name,
            "description": self.description,
            "IPProtocol": self.ip_protocol,
            "portRange": self.port_range,
            "ipVersion": self.ip_version,
            "loadBalancingScheme": self.load_balancing_scheme,

        }
        if self.target_proxy:
            target_type = self.target_proxy.type.lower().capitalize()
            json_data["target"] = "projects/{project}/global/target{target_type}Proxies/{target}".format(
                project=self.gcp_cloud_project.project_id, target_type=target_type,
                target=self.target_proxy.name)
        if not self.ip_address == "EPEHERMAL":
            json_data["IPAddress"] = self.ip_address

        return json_data


class GcpTargetProxy(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    TYPE_KEY = "type"
    STATUS_KEY = "status"
    DESCRIPTION_KEY = "description"
    URL_MAP_KEY = "url_map"

    __tablename__ = 'gcp_target_proxies'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    type = Column(String(50), Enum('HTTP', 'HTTPS'), nullable=False)
    description = Column(String(1024))

    forwarding_rule_id = Column(String(32), ForeignKey('gcp_forwarding_rules.id'), nullable=False)
    url_map = relationship('GcpUrlMap', backref='gcp_target_proxy', cascade="all, delete-orphan",
                           uselist=False)

    def __init__(self, name, type_, description=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.status = CREATING
        self.type = type_ or "HTTP"
        self.description = description

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.DESCRIPTION_KEY: self.description,
            self.TYPE_KEY: self.type,
            self.URL_MAP_KEY: self.url_map.to_json() if self.url_map else None
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "description": self.description,
            "urlMap": "projects/{project}/global/urlMaps/{url_map}".format(
                project=self.gcp_forwarding_rule.gcp_cloud_project.project_id, url_map=self.url_map.name)
        }


class GcpUrlMap(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    DESCRIPTION_KEY = "description"
    DEFAULT_BACKEND_SERVICE_KEY = "default_backend_service"
    HOST_RULE_KEY = "host_rules"

    __tablename__ = 'gcp_url_maps'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    description = Column(String(1024))
    type = Column(String(255), Enum("LOAD-BALANCER"), default="LOAD-BALANCER", nullable=False)

    target_proxy_id = Column(String(32), ForeignKey('gcp_target_proxies.id'), nullable=False)
    cloud_project_id = Column(String(32), ForeignKey('gcp_cloud_projects.id'), nullable=False)
    load_balancer_id = Column(String(32), ForeignKey('gcp_load_balancers.id'))

    default_backend_service = relationship('GcpBackendService', backref='gcp_url_map', cascade="all, delete-orphan",
                                           uselist=False)
    host_rules = relationship('GcpHostRule', backref='gcp_url_map', cascade="all, delete-orphan", lazy="dynamic")

    def __init__(self, name, type_="LOAD-BALANCER", description=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.type = type_
        self.status = CREATING
        self.description = description

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.DESCRIPTION_KEY: self.description,
            self.DEFAULT_BACKEND_SERVICE_KEY: self.default_backend_service.to_json()
            if self.default_backend_service else None,
            self.HOST_RULE_KEY: [host_rule.to_json() for host_rule in self.host_rules.all()]
        }

    def to_json_body(self):
        return {
            "name": self.name,
            "description": self.description,
            "defaultService": "projects/{project}/global/backendServices/{service}".format(
                project=self.default_backend_service.gcp_cloud_project.project_id,
                service=self.default_backend_service.name),
            "hostRules": [host.to_json_body() for host in self.host_rules.all()],
            "pathMatchers": [host.path_matcher.to_json_body() for host in self.host_rules.all()]
        }


class GcpHostRule(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    HOST_KEY = "hosts"
    PATH_MATCHER_KEY = "path_matcher"

    __tablename__ = "gcp_host_rules"

    id = Column(String(32), primary_key=True)
    hosts = Column(MutableDict.as_mutable(JSONEncodedDict))
    url_map_id = Column(String(32), ForeignKey('gcp_url_maps.id'), nullable=False)

    path_matcher = relationship('GcpPathMatcher', backref='gcp_host_rule', cascade="all, delete-orphan", uselist=False)

    def __init__(self, hosts):
        self.id = str(uuid.uuid4().hex)
        self.hosts = {self.HOST_KEY: hosts}

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.HOST_KEY: self.hosts.get(self.HOST_KEY),
            self.PATH_MATCHER_KEY: self.path_matcher.to_json() if self.path_matcher else None
        }

    def to_json_body(self):
        return {
            "hosts": self.hosts.get(self.HOST_KEY),
            "pathMatcher": self.path_matcher.name
        }


class GcpPathMatcher(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    DESCRIPTON_KEY = "description"
    DEFAULT_SERVICE_KEY = "default_service"
    PATH_RULES_KEY = "path_rules"

    __tablename__ = "gcp_path_matchers"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    host_rule_id = Column(String(32), ForeignKey('gcp_host_rules.id'), nullable=False)

    default_backend_service = relationship('GcpBackendService', backref='gcp_path_matcher',
                                           cascade="all, delete-orphan", uselist=False)
    path_rules = relationship('GcpPathRule', backref='gcp_path_matcher', cascade="all, delete-orphan", lazy="dynamic")

    def __init__(self, name, description=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.description = description

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.DESCRIPTON_KEY: self.description,
            self.DEFAULT_SERVICE_KEY: self.default_backend_service.to_json() if self.default_backend_service else None,
            self.PATH_RULES_KEY: [path.to_json() for path in self.path_rules.all()]
        }

    def to_json_body(self):
        json_data = {
            "name": self.name,
            "description": self.description,
            "defaultService": "projects/{project}/global/backendServices/{service}".format(
                project=self.gcp_host_rule.gcp_url_map.gcp_cloud_project.project_id,
                service=self.default_backend_service.name)
        }
        if self.path_rules:
            path_rules_list = list()
            for path_rule in self.path_rules.all():
                path_rules_list.extend(path_rule.paths.get(path_rule.PATHS_KEY))
            json_data["pathRules"] = path_rules_list
        return json_data


class GcpPathRule(db.Model):
    ID_KEY = "id"
    SERVICE_KEY = "service"
    PATHS_KEY = "paths"

    __tablename__ = "gcp_path_rules"

    id = Column(String(32), primary_key=True)
    paths = Column(MutableDict.as_mutable(JSONEncodedDict))
    path_matcher_id = Column(String(32), ForeignKey('gcp_path_matchers.id'), nullable=False)
    service = relationship('GcpBackendService', backref='gcp_path_rule', cascade="all, delete-orphan", uselist=False)

    def __init__(self, paths):
        self.id = str(uuid.uuid4().hex)
        self.paths = {self.PATHS_KEY: paths}

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.PATHS_KEY: self.paths.get(self.PATHS_KEY),
            self.SERVICE_KEY: self.service.to_json() if self.service else None
        }


class GcpIpProtocol(db.Model):
    ID_KEY = "id"
    PROTOCOL_KEY = "protocol"
    PORT_KEY = "ports"

    __tablename__ = 'gcp_ip_protocols'

    id = Column(String(32), primary_key=True)
    protocol = Column(String(255), nullable=False)
    ports = Column(MutableDict.as_mutable(JSONEncodedDict))

    firewall_rule_id = Column(String(32), ForeignKey('gcp_firewall_rules.id'), nullable=False)

    def __init__(self, protocol, ports=None, firewall_rule_id=None):
        self.id = self.id = str(uuid.uuid4().hex)
        self.protocol = protocol
        self.ports = {self.PORT_KEY: ports}
        self.firewall_rule_id = firewall_rule_id

    def make_copy(self):
        return GcpIpProtocol(self.protocol, self.ports.get(self.PORT_KEY))

    def params_eq(self, other):
        if not type(self) == type(other):
            return False

        if not self.name == other.name:
            return False

        if self.ports.get(self.PORT_KEY) and not other.ports.get(other.PORT_KEY):
            return False

        if other.ports.get(other.PORT_KEY) and not self.ports.get(self.PORT_KEY):
            return False

        if self.ports.get(self.PORT_KEY) and other.ports.get(self.PORT_KEY):
            if not (set(self.ports.get(self.PORT_KEY)) == set(other.ports.get(self.PORT_KEY))):
                return False

        return True

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.PROTOCOL_KEY: self.protocol,
            self.PORT_KEY: self.ports.get(self.PORT_KEY) if self.ports else None
        }

    def to_json_body(self):
        return {
            "IPProtocol": self.protocol,
            "ports": self.ports.get(self.PORT_KEY) if self.ports.get(self.PORT_KEY) else []
        }

    def add_update_db(self, existing=None):
        if existing:
            if not self.params_eq(existing):
                current_app.logger.debug("Updating IP Protocol '{}' to DB".format(self.name))
                existing.protocol = self.protocol
                existing.ports = self.ports
                db.session.commit()
        else:
            current_app.logger.debug("Adding IP Protocol '{}' to DB".format(self.name))
            db.session.add(self)
            db.session.commit()
