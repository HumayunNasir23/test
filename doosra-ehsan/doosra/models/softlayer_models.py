import uuid

from sqlalchemy import Column, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from doosra import db
from doosra.common.utils import encrypt_api_key


class SoftlayerCloud(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    STATUS_KEY = "status"
    USERNAME_KEY = "username"

    __tablename__ = 'softlayer_clouds'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), Enum("AUTHENTICATING", "VALID", "INVALID"), nullable=False)
    username = Column(String(255), nullable=False)
    api_key = Column(String(500), nullable=False)
    ibm_cloud_account_id = Column(String(32), nullable=False)

    project_id = Column(String(32), ForeignKey('projects.id'), nullable=False)

    workspaces = relationship(
        "WorkSpace",
        backref="soflayer_cloud",
        lazy="dynamic",
    )

    def __init__(self, name, username, api_key, project_id, ibm_cloud_account_id):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.username = username
        self.api_key = encrypt_api_key(api_key)
        self.ibm_cloud_account_id = ibm_cloud_account_id
        self.status = "AUTHENTICATING"
        self.project_id = project_id

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.STATUS_KEY: self.status,
            self.USERNAME_KEY: self.username
        }
