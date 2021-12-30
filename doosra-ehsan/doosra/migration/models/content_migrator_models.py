from sqlalchemy import (
    Column,
    Integer,
    JSON
)
from doosra import db


class CMModels(db.Model):
    SOFTLAYER_VSI_ID_KEY = "softLayer_vsi_id"
    CM_META_DATA_KEY = "cm_meta_data"

    __tablename__ = "cm_models"

    softlayer_vsi_id = Column(Integer, nullable=True, primary_key=True)
    cm_meta_data = Column(JSON, default={})

    def __init__(self, softlayer_vsi_id, cm_meta_data):
        self.softlayer_vsi_id = softlayer_vsi_id
        self.cm_meta_data = cm_meta_data

    def to_json(self):
        return {
            self.SOFTLAYER_VSI_ID_KEY: self.softlayer_vsi_id,
            self.CM_META_DATA_KEY: self.cm_meta_data
        }
