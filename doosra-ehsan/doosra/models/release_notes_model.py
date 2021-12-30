import uuid
from datetime import datetime


from sqlalchemy import Column, DateTime, ForeignKey, PrimaryKeyConstraint, String, Text
from sqlalchemy.orm import backref, relationship

from doosra import db
from doosra.models.users_models import Project
from doosra.models.common_models import JSONEncodedDict, MutableDict


class ReleaseNote(db.Model):
    """ Release note model for storing release note related information. """

    ID_KEY = "id"
    TITLE_KEY = "title"
    BODY_KEY = "body"
    RELEASE_DATE_KEY = "release_date"
    VERSION_KEY = "version"
    URL_KEY = "url"

    __tablename__ = "release_notes"

    id = Column(String(32), primary_key=True)
    title = Column(String(255), nullable=False)
    body = Column(MutableDict.as_mutable(JSONEncodedDict), nullable=False)
    release_date = Column(DateTime, nullable=False)
    url = Column(String(255), nullable=True)
    version = Column(String(32), nullable=True)

    project_release_notes = relationship('ProjectReleaseNotes', backref='release_notes', cascade="all, delete-orphan",
                                         lazy='dynamic')

    def __init__(self, title, body, url=None, version=None):
        self.id = str(uuid.uuid4().hex)
        self.title = title
        self.body = body
        self.release_date = datetime.utcnow()
        self.url = url
        self.version = version

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.TITLE_KEY: self.title,
            self.BODY_KEY: self.body,
            self.RELEASE_DATE_KEY: str(self.release_date),
            self.URL_KEY: self.url,
            self.VERSION_KEY: self.version
        }

    def update_user_release_notes(self):
        projects = Project.query.all()
        for project in projects:
            self.project_release_notes.append(ProjectReleaseNotes(project_id=project.id))


class ProjectReleaseNotes(db.Model):
    __tablename__ = 'project_release_notes'

    id = Column(String(32), primary_key=True)
    release_notes_id = Column(String(32), ForeignKey('release_notes.id'), nullable=False)
    project_id = Column(String(255), ForeignKey('projects.id'), nullable=False)

    def __init__(self, project_id):
        self.id = str(uuid.uuid4().hex)
        self.project_id = project_id
