import uuid

from sqlalchemy import Column, Enum, ForeignKey, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT

from doosra import db


class Template(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    DESCRIPTION_KEY = "description"
    TYPE_KEY = "type"
    CLOUD_TYPE_KEY = "cloud_type"
    SCHEMA_KEY = "schema"
    SCHEMA_TYPE_KEY = "schema_type"

    __tablename__ = 'templates'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    type = Column(Enum("PRE_DEFINED", "USER_MANAGED"), default="USER_MANAGED", nullable=False)
    cloud_type = Column(Enum("IBM", "GCP"), nullable=False)
    schema_type = Column(Enum("VPC", "INSTANCE", "ACL", "SECURITY_GROUP", "SUBNET"), nullable=False)
    schema = Column(MEDIUMTEXT, nullable=True)

    project_id = Column(String(32), ForeignKey('projects.id'))

    def __init__(self, name, schema, schema_type, cloud_type, description=None, project_id=None, type_=None):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.type = type_ or "USER_MANAGED"
        self.schema = schema
        self.cloud_type = cloud_type
        self.schema_type = schema_type
        self.description = description
        self.project_id = project_id

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.DESCRIPTION_KEY: self.description,
            self.TYPE_KEY: self.type,
            self.CLOUD_TYPE_KEY: self.cloud_type,
            self.SCHEMA_KEY: self.schema,
            self.SCHEMA_TYPE_KEY: self.schema_type
        }

    @property
    def is_pre_built(self):
        return self.type == "PRE_BUILT"
