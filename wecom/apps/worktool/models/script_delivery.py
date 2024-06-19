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


class ScriptDelivery(BaseModel):
    __tablename__ = 'wecom_script_delivery'

    rid = Column(db.String(100), nullable=False, server_default='')
    output = db.Column(db.Text, nullable=False, default='', server_default='')
    author = Column(db.String(100), nullable=False, server_default='')                  # 作者
    work_name = Column(db.String(200), nullable=False, server_default='')               # 作品名
    theme = Column(db.String(200), nullable=False, server_default='')                   # 题材类型
    core_highlight = Column(db.String(500), nullable=False, server_default='')          # 核心亮点
    core_idea = Column(db.String(500), nullable=False, server_default='')               # 核心创意
    pit_date = Column(db.String(20), nullable=False, server_default='')                 # 开坑时间
    ai_score = Column(db.String(20), nullable=False, server_default='')                  # AI评分
    detail_url = Column(db.String(500), nullable=False, server_default='')              # 评估详情见链接
    src_url = Column(db.String(500), nullable=False, server_default='')                 # 原文链接
    uniq_id = Column(db.String(6), unique=True, nullable=False, server_default='')      # 唯一字段
    is_pushed = Column(db.Boolean, nullable=False, default=False, server_default='0')   # 是否推送
    group_name = Column(db.String(100), nullable=False, server_default='')              # 要推送的群组
    push_date = Column(db.String(10), nullable=False, server_default='')                # 要推送的日期
    is_delete = Column(db.Boolean, nullable=False, default=False, server_default='0')   # 是否删除
    pushed_time = Column(db.DateTime)                                                   # 推送时间
    finished_time = Column(db.DateTime)                                                 # 数据接收完成时间

    @classmethod
    def get_unique_id(cls, k=6):
        query = cls.query.options(load_only(cls.uniq_id)).all()
        uniq_ids_set = {obj.uniq_id for obj in query}

        retry_time = 0
        while retry_time < len(uniq_ids_set) + 1:
            retry_time += 1
            uniq_seq = "".join(random.choices(string.ascii_letters, k=k))

            if uniq_seq not in uniq_ids_set:
                return uniq_seq

        raise ValueError("[ScriptDelivery] 计算唯一id失败")

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
    def get_required_script_delivery_list(cls):
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
    def update_push(cls, uniq_ids):
        cls.query.filter(cls.uniq_id.in_(uniq_ids)).update({"is_pushed": 1, "pushed_time": func.now()})
        db.session.commit()




