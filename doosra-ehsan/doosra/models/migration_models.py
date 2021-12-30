import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.hybrid import hybrid_property

from doosra import db
from doosra.common.consts import BACKGROUND, CREATED, FAILED, IN_PROGRESS, PENDING, SUCCESS


class MigrationTask(db.Model):
    ID_KEY = "id"
    STATUS_KEY = "status"
    STARTED_AT_KEY = "started_at"
    RESULT_KEY = "result"

    __tablename__ = 'migration_tasks'

    id = Column(String(100), primary_key=True)
    _status = Column(Enum(CREATED, SUCCESS, FAILED), nullable=False)
    started_at = Column(DateTime)
    last_updated_at = Column(DateTime, onupdate=datetime.utcnow())
    completed_at = Column(DateTime)
    result = Column(MEDIUMTEXT, nullable=True)

    project_id = Column(String(32), ForeignKey('projects.id'), nullable=False)

    def __init__(self, project_id=None):
        self.id = str(uuid.uuid4().hex)
        self.project_id = project_id
        self.status = CREATED
        self.started_at = datetime.utcnow()

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
            self.STARTED_AT_KEY: self.started_at,
            self.RESULT_KEY: self.result
        }


class SecondaryVolumeMigrationTask(db.Model):
    ID_KEY = "id"
    STATUS_KEY = "status"
    CREATED_AT_KEY = "created_at"
    STARTED_AT_KEY = "started_at"
    FINISHED_AT_KEY = "finished_at"
    MESSAGE_KEY = "message"
    VOLUME_CAPACITY = "volume_capacity"
    VOLUME_ATTACHED = "volume_attached"
    INSTANCE_ID = "instance_id"
    REPORT = "report"

    __tablename__ = 'secondary_volume_migration_tasks'

    id = Column(String(100), primary_key=True)
    __status = Column("status", Enum(IN_PROGRESS, FAILED, SUCCESS, CREATED, BACKGROUND, PENDING), nullable=False)
    created_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    message = Column(MEDIUMTEXT, nullable=True)
    volume_attached = Column(Boolean, default=False)
    volume_capacity = Column(Integer, default=None)
    report = Column(JSON)

    instance_id = Column("instance_id", String(32), ForeignKey("ibm_instances.id"), nullable=False)

    def __init__(self, instance_id, volume_attached=False, volume_capacity=None,
                 status=PENDING, message=None, finished_at=None, report=None):
        self.id = str(uuid.uuid4().hex)
        self.__status = status
        self.created_at = datetime.utcnow()
        self.finished_at = finished_at
        self.message = message
        self.volume_attached = volume_attached
        self.volume_capacity = volume_capacity
        self.instance_id = instance_id
        self.report = report

    @hybrid_property
    def status(self):
        return self.__status

    @status.setter
    def status(self, value):
        self.__status = value
        if value == SUCCESS or value == FAILED:
            self.finished_at = datetime.utcnow()

        if value == IN_PROGRESS:
            self.started_at = datetime.utcnow()

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.STATUS_KEY: self.status,
            self.CREATED_AT_KEY: self.created_at,
            self.STARTED_AT_KEY: self.started_at,
            self.FINISHED_AT_KEY: self.finished_at,
            self.MESSAGE_KEY: self.message,
            self.VOLUME_ATTACHED: self.volume_attached,
            self.VOLUME_CAPACITY: self.volume_capacity,
            self.INSTANCE_ID: self.instance_id,
            self.REPORT: self.report
        }


class KubernetesClusterMigrationTask(db.Model):
    ID_KEY = "id"
    STARTED_AT = "started_at"
    COMPLETED_AT = "completed_at"
    MESSAGE_KEY = "message"
    SOURCE_CLUSTER = "source_cluster"
    TARGET_CLUSTER = "target_cluster"
    COS = "cos"

    __tablename__ = 'kubernetes_cluster_migration_tasks'

    id = Column(String(100), primary_key=True)
    base_task_id = Column(String(32), nullable=False)
    source_cluster = Column(JSON())
    target_cluster = Column(JSON())
    cos = Column(JSON())
    started_at = Column(DateTime)
    message = Column(String(1024))
    completed_at = Column(DateTime)

    def __init__(self, base_task_id, cos=None, source_cluster=None, target_cluster=None):

        self.id = str(uuid.uuid4().hex)
        self.base_task_id = base_task_id
        self.target_cluster = target_cluster
        self.source_cluster = source_cluster
        self.cos = cos
        self.started_at = datetime.utcnow()
