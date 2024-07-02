import time
import string
import random
from datetime import datetime

from faker import Faker

from sqlalchemy import func
from sqlalchemy.orm import load_only
from sqlalchemy import Column, Integer, String, Float, Enum, Text

from wecom.utils.enums import RebotType
from .workflowrunrecord import WorkflowRunRecord
from wecom.core.database import db, Column, BaseModel


class RebotDetection(BaseModel):
    __tablename__ = 'wecom_rebot_detection'

    text = Column(db.String(2000), nullable=False, server_default='')                       # 发送或接收文本
    send_timestamp = Column(db.Integer, nullable=False, server_default='0')                 # 发送时间戳
    reply_timestamp = Column(db.Integer, nullable=False, server_default='0')                # 回复时间戳
    # opt_type = Column(db.SmallInteger, nullable=False, server_default='0')              # 类型
    # batch_seq = Column(db.String(50), nullable=False, server_default='')                # 批次序列
    code = Column(db.Integer, nullable=False, server_default='0')                           # 发送后机器人接口返回的状态码
    message = Column(db.String(200), nullable=False, server_default='')                     # 发送后机器人接口返回的信息
    msg_id = Column(db.String(50), nullable=False, server_default='')                       # 发送后机器人接口返回的信息ID
    reply_times = Column(db.SmallInteger, nullable=False, server_default='0')               # 探测回复的次数
    is_reply_ok = Column(db.Boolean, nullable=False, default=False, server_default='0')     # 机器人回复是否成功

    @classmethod
    def create(cls, opt_type: RebotType, text: str = None, batch_seq: str = None, **kwargs):
        fields = cls.fields()
        values = {key: val for key, val in kwargs.items() if key in fields}

        if not text:
            fake = Faker(locale="zh_CN")
            text = short_sentence = fake.sentence()

        if batch_seq is None:
            random_key = "".join(random.choices(string.ascii_letters, k=6))
            batch_seq = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + random_key

        instance = cls(text=text, send_timestamp=int(time.time()), **values)
        db.session.add(instance)
        db.session.commit()

        return instance

    @classmethod
    def get_by_msg_id(cls, msg_id: str, opt_type: RebotType):
        return cls.query.filter_by(msg_id=msg_id, opt_type=opt_type.value).order_by(cls.id.asc()).first()

    @classmethod
    def get_latest_from_already_sent(cls):
        return cls.query.order_by(cls.id.desc()).first()

    @classmethod
    def update_reply_times_by_id(cls, sent_pk):
        cls.query.filter_by(id=sent_pk).update({cls.reply_times: cls.reply_times + 1}, synchronize_session=False)
        db.session.commit()

    @classmethod
    def update_reply_ok_by_id(cls, sent_pk):
        cls.query.filter_by(id=sent_pk).update({"is_reply_ok": 1})
        db.session.commit()
