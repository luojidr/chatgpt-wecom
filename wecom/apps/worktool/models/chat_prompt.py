import time
import traceback
from typing import List

from sqlalchemy import Index
from sqlalchemy import Column, Integer, String, BigInteger, Boolean

from database import BaseModel, session
from database.models.user import User, WXUser
from common.log import logger


class ChatPrompt(BaseModel):
    __tablename__ = 'chat_prompt'

    user_id = Column(Integer, nullable=False, server_default='0')
    chat_log_id = Column(Integer, nullable=False, server_default='0')
    seq_no = Column(String(20), nullable=False, server_default='')  # 多个提示词的序列号
    prompt = Column(String(1000), nullable=False, server_default='')
    timestamp = Column(BigInteger, nullable=False, server_default='0')
    is_group = Column(Boolean, nullable=False, server_default="0")

    Index("idx_timestamp", "timestamp")
    Index("idx_userid_chatlogid_seq_no", "user_id", "chat_log_id", "seq_no")

    @classmethod
    def create(cls, user_id: int, chat_log_id: int, prompts: List[str], is_group: bool = False):
        instances = []

        try:
            for no, prompt in enumerate(prompts, 1):
                obj = cls(
                    user_id=user_id, chat_log_id=chat_log_id, seq_no=no,
                    prompt=prompt, timestamp=int(time.time() * 1000),
                    is_group=is_group,
                )
                instances.append(obj)
        except Exception as e:
            logger.error("ChatPrompt create err: %s", e)
            logger.error(traceback.format_exc())
        else:
            if instances:
                session.add_all(instances)
                session.commit()

    @classmethod
    def get_potential_prompt(cls, userid: str, seq_no: int):
        user = session.query(User).filter_by(userid=userid).first()
        if user is None:
            logger.error("用户(%s)不存在", userid)
            return

        user_id = user.id
        # chat_log_obj = session.query(ChatLog).filter_by(user_id=user_id).order_by(ChatLog.id.desc()).first()
        # if chat_log_obj is None:
        #     logger.error("用户(%s)还未进行聊天", userid)
        #     return

        instance = session.query(cls)\
            .filter_by(
                user_id=user_id,
                # chat_log_id=chat_log_obj.id,
                seq_no=seq_no)\
            .order_by(cls.timestamp.desc())\
            .first()

        return instance.prompt if instance else ""

    @classmethod
    def get_wx_potential_prompt(cls, session_id: str, seq_no: str, is_group: bool = False):
        wx_user = session.query(WXUser).filter_by(username=session_id).first()
        if wx_user is None:
            logger.error("用户(%s)不存在", session_id)
            return

        user_id = wx_user.user_id
        instance = session.query(cls) \
            .filter_by(
            user_id=user_id,
            is_group=is_group,
            # chat_log_id=chat_log_obj.id,
            seq_no=seq_no) \
            .order_by(cls.timestamp.desc()) \
            .first()

        return instance.prompt if instance else ""
