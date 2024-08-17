from wecom.core.database import db, Column, BaseModel


class Workflow(db.Model):
    __bind_key__ = "workflow"
    __tablename__ = "workflow"

    wid = Column(db.String(255), nullable=False, primary_key=True)
    user_id = Column(db.String(255), nullable=False, index=True)
    status = Column(db.String(50), nullable=False)
    title = Column(db.String(200), nullable=False)
    data = Column(db.Text, nullable=False)
    brief = Column(db.String(255), nullable=False)




