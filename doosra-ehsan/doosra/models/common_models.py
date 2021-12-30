import uuid
import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, VARCHAR

from doosra import db
from doosra.common.consts import CREATED, FAILED, SUCCESS


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Ref: http://docs.sqlalchemy.org/en/rel_1_0/orm/extensions/mutable.html
    """
    impl = VARCHAR(1024)

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionaries to MutableDict."""
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        """Detect dictionary set events and emit change events."""
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        """Detect dictionary del events and emit change events."""
        dict.__delitem__(self, key)
        self.changed()


class SyncTask(db.Model):
    ID_KEY = "id"
    STATUS_KEY = "status"
    TYPE_KEY = "type"
    RESULT_KEY = "result"
    CLOUD_TYPE_KEY = "cloud_type"
    STARTED_AT_KEY = "started_at"
    COMPLETED_AT_KEY = "completed_at"

    __tablename__ = "sync_tasks"

    id = Column(String(100), primary_key=True)
    resource_id = Column(String(32), nullable=True)
    type = Column(String(32), Enum("INSTANCE", "IMAGE"), nullable=False)
    cloud_type = Column(String(32), Enum("GCP", "IBM", "SOFTLAYER"), nullable=False)
    _status = Column(String(32), Enum(CREATED, SUCCESS, FAILED), nullable=False)
    result = Column(MutableDict.as_mutable(JSONEncodedDict), nullable=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)

    project_id = Column(String(32), ForeignKey("projects.id"))

    def __init__(self, cloud_type, type_, project_id, resource_id=None):
        self.id = str(uuid.uuid4().hex)
        self.resource_id = resource_id
        self.status = CREATED
        self.cloud_type = cloud_type
        self.type = type_
        self.project_id = project_id
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
            self.COMPLETED_AT_KEY: self.completed_at,
            self.RESULT_KEY: self.result,
            self.CLOUD_TYPE_KEY: self.cloud_type
        }
