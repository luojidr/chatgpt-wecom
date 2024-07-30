from wecom.core.database import db, Column, BaseModel


class ContractedOpus(BaseModel):
    __tablename__ = 'contracted_opus_book'
    __bind_key__ = "novel_crawler"

    web_type = Column(db.String(100), nullable=False, server_default='')
    contract_type = Column(db.String(100), nullable=False, server_default='')
    title = Column(db.String(100), nullable=False, server_default='')
    author = Column(db.String(100), nullable=False, server_default='')
    genre = Column(db.String(100), nullable=False, server_default='')
    contract_date = Column(db.String(100), nullable=False, server_default='')

