import uuid
from datetime import datetime

from flask import current_app
from passlib.apps import custom_app_context as pwd_context
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from doosra import db
from doosra.models.common_models import MutableDict, JSONEncodedDict


class User(db.Model):
    """ User Model for storing User related details """
    ID_KEY = "id"
    EMAIL_KEY = "email"
    DATA_KEY = "data"

    __tablename__ = "users"

    id = Column(String(32), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    data = Column(MutableDict.as_mutable(JSONEncodedDict))

    project = relationship('Project', backref='user', cascade="all, delete-orphan", uselist=False)
    billing = relationship("BillingResource", backref='user', cascade="all, delete-orphan", lazy='dynamic')

    def __init__(self, _id, email):
        self.id = _id
        self.email = email

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.EMAIL_KEY: self.email,
            self.DATA_KEY: self.data
        }


class Project(db.Model):
    ID_KEY = "id"

    __tablename__ = 'projects'

    id = Column(String(32), primary_key=True)
    user_id = Column(String(32), ForeignKey('users.id'), nullable=False)

    gcp_clouds = relationship('GcpCloud', backref='project', cascade="all, delete-orphan", lazy='dynamic')
    gcp_cloud_projects = relationship(
        'GcpCloudProject', backref='project', cascade="all, delete-orphan", lazy='dynamic')
    ibm_clouds = relationship('IBMCloud', backref='project', cascade="all, delete-orphan", lazy='dynamic')
    migration_tasks = relationship('MigrationTask', backref='project', cascade="all, delete-orphan", lazy='dynamic')
    sync_tasks = relationship('SyncTask', backref='project', cascade="all, delete-orphan", lazy='dynamic')
    templates = relationship('Template', backref='project', cascade="all, delete-orphan", lazy='dynamic')
    softlayer_clouds = relationship('SoftlayerCloud', backref='project', cascade="all, delete-orphan", lazy='dynamic')
    workspaces = relationship('WorkSpace', backref='project', cascade="all, delete-orphan", lazy='dynamic')
    project_release_notes = relationship('ProjectReleaseNotes', backref='project',
                                         cascade="all, delete-orphan", lazy='dynamic')
    billing = relationship("BillingResource", backref="project", cascade="all, delete-orphan", lazy='dynamic')

    def __init__(self, _id):
        self.id = _id

    def to_json(self):
        return {
            self.ID_KEY: self.id
        }
