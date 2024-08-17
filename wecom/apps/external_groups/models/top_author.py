from wecom.core.database import db, Column, BaseModel


class TopAuthor(BaseModel):
    __tablename__ = 'head_author'
    __bind_key__ = "novel_crawler"

    author_name = Column(db.String(100), nullable=False, server_default='')
    author_url = Column(db.String(200), nullable=False, server_default='')
    book_name = Column(db.String(50), nullable=False, server_default='')
    books_type = Column(db.String(100), nullable=False, server_default='')
    progress = Column(db.String(10), nullable=False, server_default='')
    word_count = Column(db.String(10), nullable=False, server_default='')
    issued_time = Column(db.String(20), nullable=False, server_default='')


