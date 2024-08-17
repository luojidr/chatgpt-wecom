import re
import time
import string
import random
import os.path
import traceback
from collections import namedtuple
from typing import Optional, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import load_only
from sqlalchemy import Column, Integer, String, Float, Enum, Text

from wecom.core.database import db, Column, BaseModel


class BookHash(BaseModel):
    __tablename__ = 'book_hash'
    __bind_key__ = "novel_crawler"

    book_name = Column(db.String(100), nullable=False, server_default='')
    author = Column(db.String(100), nullable=False, server_default='')
    score = Column(db.String(20), nullable=False, server_default='')
    rid = Column(db.String(100), nullable=False, server_default='')
    book_type = Column(db.String(100), nullable=False, server_default='')
    src_url = Column(db.String(500), nullable=False, server_default='')
    pit_date = Column(db.String(20), nullable=False, server_default='')


