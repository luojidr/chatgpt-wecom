from sqlalchemy.orm import load_only

from wecom.core.database import db, Column, BaseModel


class WorkflowRunRecord(db.Model):
    __bind_key__ = "workflow"
    __tablename__ = "workflowrunrecord"

    rid = Column(db.String(255), primary_key=True)
    user_id = Column(db.String(255), nullable=False, index=True)
    workflow_id = Column(db.String(255), nullable=False, index=True)
    status = Column(db.String(50), nullable=False)
    data = Column(db.Text, nullable=False)
    schedule_time = Column(db.DateTime)
    start_time = Column(db.DateTime)
    end_time = Column(db.DateTime)
    used_credits = Column(db.Integer, nullable=False)
    general_details = Column(db.Text)
    cost = Column(db.Double, nullable=False)
    parent_wid = Column(db.String(255), nullable=False)

    data_id = Column(db.Integer, nullable=False, server_default='0')
    general_details_id = Column(db.Integer, nullable=False, server_default='0')

    @classmethod
    def get_output_by_rid(cls, rid) -> str:
        obj = cls.query.options(load_only(cls.general_details)).filter_by(rid=rid).first()
        return obj and obj.general_details



