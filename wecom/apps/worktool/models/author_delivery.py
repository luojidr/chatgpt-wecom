import string
import random
import os.path
from itertools import groupby
from operator import attrgetter
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import load_only
from sqlalchemy import Column, Integer, String, Float, Enum, Text

from .workflowrunrecord import WorkflowRunRecord
from wecom.core.database import db, Column, BaseModel


class AuthorDelivery(BaseModel):
    __tablename__ = 'wecom_author_delivery'

    rid = Column(db.String(100), nullable=False, server_default='')
    author = Column(db.String(100), nullable=False, server_default='')                  # 作者
    brief = Column(db.String(100), nullable=False, server_default='')                   # 作者简介
    work_name = Column(db.String(200), nullable=False, server_default='')               # 作品名
    theme = Column(db.String(200), nullable=False, server_default='')                   # 作品题材类型

    src_url = Column(db.String(500), nullable=False, server_default='')                 # 原文链接
    platform = Column(db.String(500), nullable=False, server_default='')                # 平台
    is_pushed = Column(db.Boolean, nullable=False, default=False, server_default='0')   # 是否推送
    group_name = Column(db.String(100), nullable=False, server_default='')              # 要推送的群组
    is_delete = Column(db.Boolean, nullable=False, default=False, server_default='0')   # 是否删除
    pushed_time = Column(db.DateTime)                                                   # 推送时间
    finished_time = Column(db.DateTime)                                                 # 数据接收完成时间

    @classmethod
    def create(cls, **kwargs):
        fields = cls.fields()
        values = {key: val for key, val in kwargs.items() if key in fields}

        instance = cls.query\
            .filter_by(
                author=values.get("author"),
                work_name=values.get("work_name"),
                group_name=values.get("group_name"),
                is_delete=False
            )\
            .first()

        if instance is None:
            instance = cls(**values)
        else:
            for key, val in values.items():
                setattr(instance, key, val)

        instance.finished_time = func.now()
        if not instance.uniq_id:
            uniq_id = cls.get_unique_id()
            instance.uniq_id = uniq_id
            instance.detail_url = os.environ["TOP_EVALUATION_URL"] + uniq_id

        db.session.add(instance)
        db.session.commit()

        return instance

    @classmethod
    def get_object(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def get_required_author_delivery_list(cls):
        results = {}
        push_date = date.today().strftime("%Y-%m-%d")
        queryset = cls.query.filter_by(push_date=push_date, is_pushed=False, is_delete=False).all()

        # for group_name, objects in groupby(queryset, key=attrgetter("group_name")):
        for obj in queryset:
            results.setdefault(obj.group_name, []).append(obj)

        return results

    @classmethod
    def get_output_by_uniq_id(cls, uniq_id):
        obj = cls.query.filter_by(uniq_id=uniq_id).first()
        if obj:
            run_obj = WorkflowRunRecord.query\
                .options(load_only(WorkflowRunRecord.general_details))\
                .filter_by(rid=obj.rid)\
                .first()
            return run_obj and run_obj.general_details

    @classmethod
    def get_output_by_workflow_rid(cls, rid):
        obj = WorkflowRunRecord.query\
            .options(load_only(WorkflowRunRecord.general_details))\
            .filter_by(rid=rid)\
            .first()

        if obj:
            return obj.general_details

    @classmethod
    def get_latest_push_date_by_group_name(cls, group_name):
        objs = cls.query\
            .options(load_only(cls.push_date))\
            .filter_by(group_name=group_name)\
            .order_by(cls.push_date.desc())\
            .limit(2)\
            .all()

        if not objs:
            is_new = True
            push_date = date.today()
        else:
            push_date = datetime.strptime(objs[0].push_date, "%Y-%m-%d").date()

            if len(objs) == 1:
                is_new = False
            else:
                if objs[0].push_date == objs[1].push_date:
                    is_new = True
                    push_date = push_date + timedelta(days=1)
                else:
                    is_new = False

        return is_new, push_date

    @classmethod
    def update_push_by_ids(cls, ids):
        cls.query.filter(cls.id.in_(ids)).update({"is_pushed": 1, "pushed_time": func.now()})
        db.session.commit()




