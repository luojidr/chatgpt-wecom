from wecom.core.database import db, Column, BaseModel


class CrwalerAuthor(db.Model):
    __bind_key__ = "workflow"
    __tablename__ = "xxxxxxxx"

    rid = Column(db.String(255), primary_key=True)
    author = Column(db.String(255), nullable=False, index=True)
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



