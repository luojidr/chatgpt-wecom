import string
import random
import os.path
from itertools import groupby
from operator import attrgetter
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Any

from sqlalchemy import func
from sqlalchemy.orm import load_only
from sqlalchemy import Column, Integer, String, Float, Enum, Text, SmallInteger

from .workflowrunrecord import WorkflowRunRecord
from wecom.core.database import db, Column, BaseModel


class AuthorDelivery(BaseModel):
    __tablename__ = 'wecom_author_delivery'

    rid = Column(db.String(100), nullable=False, server_default='')
    author = Column(db.String(100), nullable=False, server_default='')                      # 作者
    brief = Column(db.String(300), nullable=False, server_default='')                       # 作者简介
    work_name = Column(db.String(200), nullable=False, server_default='')                   # 作品名
    theme = Column(db.String(200), nullable=False, server_default='')                       # 作品题材类型

    src_url = Column(db.String(500), nullable=False, server_default='')                     # 原文链接
    platform = Column(db.String(500), nullable=False, server_default='')                    # 平台
    is_pushed = Column(db.Boolean, nullable=False, default=False, server_default='0')       # 是否推送

    # 0: 未调用工作流 1：调用工作流成功并执行中 2：工作流执行结束
    workflow_state = Column(db.SmallInteger, nullable=False, server_default='0')             # 调用工作流是否完成

    group_name = Column(db.String(100), nullable=False, server_default='')                  # 要推送的群组
    push_date = Column(db.String(10), nullable=False, server_default='')                    # 要推送的日期
    batch_id = Column(db.String(6), unique=True, nullable=False, server_default='')         # 批次
    message_id = Column(db.String(50), unique=True, nullable=False, server_default='')      # 推送消息id
    is_delete = Column(db.Boolean, nullable=False, default=False, server_default='0')       # 是否删除
    retry_times = Column(db.Integer, nullable=False, default=0, server_default='0')         # 重试次数
    pushed_time = Column(db.DateTime)                                                       # 推送时间
    finished_time = Column(db.DateTime)                                                     # 数据接收完成时间

    @classmethod
    def create(cls, **kwargs):
        fields = cls.fields()
        values = {key: val for key, val in kwargs.items() if key in fields}

        instance = cls.query\
            .filter_by(
                author=values.get("author"),
                work_name=values.get("work_name"),
                group_name=values.get("group_name")
            )\
            .first()

        if instance is None:
            instance = cls(**values)
        else:
            for key, val in values.items():
                setattr(instance, key, val)

        instance.finished_time = func.now()

        db.session.add(instance)
        db.session.commit()

        return instance

    @classmethod
    def get_object(cls, **kwargs):
        return cls.query.filter_by(**kwargs).order_by(cls.id.asc()).first()

    @classmethod
    def get_more_authors_by_batch_id(cls, batch_id):
        return cls.query.filter_by(batch_id=batch_id).order_by(cls.id.asc()).offset(1).all()

    @classmethod
    def get_running_rids_by_workflow_state(cls, workflow_state):
        queryset = cls.query.options(load_only(cls.rid)).filter_by(workflow_state=workflow_state).all()
        return list({obj.rid for obj in queryset})

    @classmethod
    def get_required_top_author_delivery_list(cls, group_name: str = None):
        results = {}
        kwargs = dict(
            workflow_state=2, is_pushed=False, is_delete=False,
            push_date=date.today().strftime("%Y-%m-%d"),
        )
        group_name and kwargs.update(group_name=group_name)
        queryset = cls.query.filter_by(**kwargs).filter(cls.retry_times < 2).order_by(cls.id.asc()).all()

        for obj in queryset:
            results.setdefault(obj.group_name, []).append(obj)

        return results

    @classmethod
    def update_push_state_by_message_id(cls, message_id: str):
        cls.query.filter_by(message_id=message_id).update(dict(is_pushed=1, pushed_time=func.now()))
        db.session.commit()

    @classmethod
    def update_message_id_by_ids(cls, ids, message_id, incr: bool = False):
        # cls.query.filter(cls.id.in_(ids)).update({cls.retry_times: cls.retry_times + 1}, synchronize_session=False)

        for obj in cls.query.filter(cls.id.in_(ids)).all():
            obj.message_id = message_id
            if incr:
                obj.retry_times = obj.retry_times + 1

        db.session.commit()

    @classmethod
    def update_workflow_by_id(cls, pk, rid, state):
        cls.query.filter_by(id=pk).update({"workflow_state": state, "rid": rid})
        db.session.commit()

    @classmethod
    def update_value_by_rid(cls, rid: str, upt_value: Dict[str, Any]):
        cls.query.filter_by(rid=rid).update(upt_value)
        db.session.commit()

    @classmethod
    def update_rid_by_id(cls, pk, rid):
        cls.query.filter_by(id=pk).update({"rid": rid})
        db.session.commit()


