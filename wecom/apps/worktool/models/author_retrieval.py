import json
from typing import List, Dict, Any

from wecom.core.database import db, Column, BaseModel


class AuthorRetrieval(BaseModel):
    __tablename__ = 'wecom_author_retrieval'

    # uniq: 弃用工作流运行结果rid，采用本地调用，随机生成 session_id
    uniq = Column(db.String(100), nullable=False, unique=True, server_default='')
    bing_results = Column(db.Text, nullable=False, server_default='')                        # BingSearch结果
    llm_content = Column(db.String(5000), nullable=False, server_default='')                     # 大模型调用的结果

    @classmethod
    def create(cls, uniq: str, bing_results: List[Dict[str, Any]], llm_content: str):
        instance = cls(
            uniq=uniq,
            bing_results=json.loads(bing_results),
            llm_content=llm_content
        )

        db.session.add(instance)
        db.session.commit()

        return instance
