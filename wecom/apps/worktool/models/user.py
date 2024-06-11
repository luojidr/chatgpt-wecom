import random
import string
import traceback

from sqlalchemy.orm import load_only
from sqlalchemy import Column, Enum, String, Boolean, Integer

from database import BaseModel, session
from common.log import logger


class User(BaseModel):
    __tablename__ = 'user'

    name = Column(String(100), nullable=False, server_default="")
    english_name = Column(String(100), nullable=False, server_default="")
    userid = Column(String(100), nullable=False, server_default="")
    position = Column(String(200), nullable=False, server_default="")
    email = Column(String(100), nullable=False, server_default="")
    mobile = Column(String(100), nullable=False, server_default="")
    source = Column(Enum("WX", "QYWX", "DING_TALK", "FEISHU"), nullable=False)
    is_enabled = Column(Boolean, nullable=False, server_default="0")
    agent_id = Column(String(100), nullable=False, server_default='')

    @classmethod
    def create_or_update(cls, **kwargs):
        logger.info("User.create_or_update => user_kwargs: %s", kwargs)

        fields = cls.fields()
        values = {key: val for key, val in kwargs.items() if key in fields}

        userid = values.get("userid")
        instance = session.query(cls).filter_by(userid=userid).first()

        if instance is None:
            instance = cls(**values)
        else:
            for key, val in values.items():
                setattr(instance, key, val)

        session.add(instance)
        session.commit()

        return instance

    @classmethod
    def get_user_by_userid(cls, userid):
        user = session.query(cls).filter_by(userid=userid).first()
        return user

    @classmethod
    def get_enabled_userid_list(cls, agent_id: str):
        """ 所有激活的用户 userid """
        users = session.query(cls).options(load_only(cls.userid)).filter_by(is_enabled=True, agent_id=agent_id).all()
        return [user.userid for user in users]


class WXUser(BaseModel):
    __tablename__ = 'wx_user'

    user_id = Column(Integer, nullable=False, server_default='0')
    username = Column(String(200), nullable=False, server_default="")  # session_id
    nickname = Column(String(200), nullable=False, server_default="")
    remark_name = Column(String(200), nullable=False, server_default="")
    # alias = Column(String(200), nullable=False, server_default="")
    signature = Column(String(500), nullable=False, server_default="")
    remark = Column(String(500), nullable=False, server_default="")
    is_enabled = Column(Boolean, nullable=False, server_default="0")

    def __str__(self):
        return "<WXUser id:%s, is_enabled: %s>" % (self.id, self.is_enabled)

    @classmethod
    def get_unique_user_id(cls, k=6):
        query = session.query(cls).options(load_only(cls.user_id)).all()
        user_ids_set = {obj.user_id for obj in query}

        retry_time = 0
        while retry_time < len(user_ids_set) + 1:
            retry_time += 1
            uniq_seq = "1" + "".join(random.choices(string.digits, k=k - 1))
            user_id = int(uniq_seq)

            if user_id not in user_ids_set:
                return user_id

        raise ValueError("[WXUser] 计算用户唯一id失败")

    @classmethod
    def save_batch_users(cls, member_list):
        try:
            for member in member_list:
                username = member.get("UserName", "")
                nickname = member.get("NickName", "")
                remark_name = member.get("RemarkName", "")
                signature = member.get("Signature", "")
                alias = member.get("Alias", "")

                cls.create_or_update(
                    nickname=nickname, remark_name=remark_name,
                    username=username, signature=signature,
                    # alias=alias,
                    is_enabled=True, force=False
                )
                session.commit()
        except Exception as e:
            logger.error("WXUser => err: %s", e)
            logger.error(traceback.format_exc())

    @classmethod
    def create_or_update(cls, nickname, remark_name, force=True, **kwargs):
        fields = cls.fields()
        values = {key: val for key, val in kwargs.items() if key in fields}
        values.pop("user_id", None)

        user = session.query(cls).filter_by(nickname=nickname, remark_name=remark_name).first()
        if user is None:
            user = cls(nickname=nickname, remark_name=remark_name, **kwargs)
        else:
            for key, val in values.items():
                setattr(user, key, val)

        if not user.user_id:
            user.user_id = cls.get_unique_user_id()

        session.add(user)
        if force:
            session.commit()

        return user

    @classmethod
    def get_user_by_username(cls, username):
        user = session.query(cls).filter_by(username=username).first()
        return user

