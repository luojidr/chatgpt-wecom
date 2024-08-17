import json
from typing import List, Dict, Any

from wecom.core.database import db, Column, BaseModel


class AuthorRetrieval(BaseModel):
    __tablename__ = 'wecom_author_retrieval'

    author = Column(db.String(100), nullable=False, server_default='')                      # 作者
    platform = Column(db.String(100), nullable=False, server_default='')                    # 平台
    brief = Column(db.String(300), nullable=False, server_default='')                       # 作者简介
    is_adapt = Column(db.Boolean, nullable=False, default=False, server_default='0')        # 是否有影视改编作品
    is_enabled = Column(db.Boolean, nullable=False, default=False, server_default='0')      # 是否可用

    # uniq: 弃用工作流运行结果rid，采用本地调用，随机生成 session_id
    uniq = Column(db.String(100), nullable=False, unique=True, server_default='')
    bing_results = Column(db.Text, nullable=False, server_default='')                        # BingSearch结果
    llm_content = Column(db.String(5000), nullable=False, server_default='')                 # 大模型调用的结果
    is_delete = Column(db.Boolean, nullable=False, default=False, server_default='0')        # 是否删除

    @classmethod
    def create(cls, **kwargs):
        fields = cls.fields()
        values = {key: val for key, val in kwargs.items() if key in fields}

        instance = cls(**values)

        db.session.add(instance)
        db.session.commit()

        return instance

    @classmethod
    def get_author_retrieval(cls, author: str, platform: str):
        return cls.query.filter_by(author=author, platform=platform, is_delete=False).first()
