import uuid

from sqlalchemy import Column, String, Boolean

from doosra import db


class IBMDashboardSetting(db.Model):
    ID_KEY = "id"
    NAME_KEY = "name"
    PIN_STATUS_KEY = "pin_status"
    USER_ID_KEY = "user_id"

    __tablename__ = "ibm_dashboard_settings"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    pin_status = Column(Boolean, default=True, nullable=True)
    user_id = Column(String(32), nullable=False)

    def __init__(self, name, user_id, pin_status=True):
        self.id = str(uuid.uuid4().hex)
        self.name = name
        self.pin_status = pin_status
        self.user_id = user_id

    def to_json(self):
        return {
            self.ID_KEY: self.id,
            self.NAME_KEY: self.name,
            self.PIN_STATUS_KEY: self.pin_status,
            self.USER_ID_KEY: self.user_id
        }
