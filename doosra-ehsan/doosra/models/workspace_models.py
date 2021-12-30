import uuid

from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    String,
    desc
)
from sqlalchemy.orm import relationship

from doosra import db
from doosra.common.consts import COMPLETED, IN_PROGRESS
from doosra.models import IBMTask
from doosra.models.common_models import JSONEncodedDict, MutableDict


class WorkSpace(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    TYPE_KEY = "type"
    SOFTLAYER_ID_KEY = "softlayer_cloud_id"
    VPC_KEY = "vpc"
    STATUS_KEY = "status"
    REPORT_TASK_ID = "report_task_id"

    __tablename__ = 'workspaces'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum("IBM", "GCP"), default="IBM", nullable=False)
    request_metadata = Column(MutableDict.as_mutable(JSONEncodedDict))
    _status = Column(Enum(IN_PROGRESS, COMPLETED), nullable=False)

    softlayer_id = Column(String(32), ForeignKey("softlayer_clouds.id"), nullable=True)
    project_id = Column(String(32), ForeignKey('projects.id'), nullable=False)

    ibm_vpc_network = relationship("IBMVpcNetwork", backref="workspace", uselist=False)

    def __init__(self, name, type_=None, request_metadata=None, softlayer_id=None, project_id=None):
        self.id = str(uuid.uuid4().hex)
        self.status = IN_PROGRESS
        self.name = name
        self.type = type_ or "IBM"
        self.request_metadata = request_metadata or {
            "ssh_keys": [],
            "ike_policies": [],
            "ipsec_policies": [],
            "vpns": [],
            "instances": [],
            "load_balancers": [],
            "security_groups": [],
            "acls": []
        }
        self.softlayer_id = softlayer_id
        self.project_id = project_id

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    def get_resource_task_id(self):
        """
        This method return resource task id.
        :return:
        """
        task = db.session.query(IBMTask).filter(
            IBMTask.resource_id == self.id, IBMTask.report.isnot(None)).order_by(desc(IBMTask.started_at)).first()

        return task.id if task else None

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.TYPE_KEY: self.type,
            self.SOFTLAYER_ID_KEY: self.softlayer_id,
            self.STATUS_KEY: self.status,
            self.REPORT_TASK_ID: self.ibm_vpc_network.get_resource_task_id() if self.ibm_vpc_network else None
        }
