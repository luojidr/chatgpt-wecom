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

from scripts.base import RulesBase
from .workflowrunrecord import WorkflowRunRecord
from wecom.core.database import db, Column, BaseModel


class OutputDelivery(BaseModel):
    __tablename__ = 'wecom_output_delivery'

    rid = Column(db.String(100), nullable=False, server_default='')
    output = db.Column(db.Text, nullable=False, default='', server_default='')

    @classmethod
    def get_output_text_by_rid(cls, rid):
        obj = cls.query.filter_by(rid=rid).first()
        if obj:
            return obj.output

    @classmethod
    def create(cls, rid: str):
        obj = OutputDelivery.query.filter_by(rid=rid).first()
        if obj:
            return

        instance = None
        runrecord_obj = WorkflowRunRecord.query\
            .options(load_only(WorkflowRunRecord.general_details))\
            .filter_by(rid=rid)\
            .first()

        if runrecord_obj:
            instance = cls(rid=rid, output=runrecord_obj.general_details)
            db.session.add(instance)
            db.session.commit()

        return instance


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
    ai_score = Column(db.Float, nullable=False, server_default='')                      # AI评分
    detail_url = Column(db.String(500), nullable=False, server_default='')              # 评估详情见链接
    src_url = Column(db.String(500), nullable=False, server_default='')                 # 原文链接
    platform = Column(db.String(500), nullable=False, server_default='')                # 平台
    uniq_id = Column(db.String(6), unique=True, nullable=False, server_default='')      # 唯一字段
    batch_id = Column(db.String(6), unique=True, nullable=False, server_default='')     # 批次
    is_pushed = Column(db.Boolean, nullable=False, default=False, server_default='0')   # 是否推送
    group_name = Column(db.String(100), nullable=False, server_default='')              # 要推送的群组
    push_date = Column(db.String(10), nullable=False, server_default='')                # 要推送的日期
    target_ai_score = Column(db.Float, nullable=False, server_default='0.0')            # 优先推送的AI评分
    message_id = Column(db.String(50), unique=True, nullable=False, server_default='')  # 推送消息id
    retry_times = Column(db.Integer, nullable=False, default=0, server_default='0')     # 推送失败尝试次数
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
    def get_object(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def get_required_script_delivery_list(cls, group_name: str = None):
        results = {}
        push_date = date.today().strftime("%Y-%m-%d")
        kwargs = dict(push_date=push_date, is_pushed=False, is_delete=False)
        group_name and kwargs.update(group_name=group_name)

        queryset = cls.query.filter_by(**kwargs).filter(cls.retry_times < 2).all()

        # for group_name, objects in groupby(queryset, key=attrgetter("group_name")):
        for obj in queryset:
            results.setdefault(obj.group_name, []).append(obj)

        return results

    @classmethod
    def query_by_ai_score(cls,
                          start_dt: Optional[datetime] = None,
                          end_dt: Optional[datetime] = None,
                          ai_score: Optional[float] = 8.5,
                          operator: str = "eq",
                          limit: Optional[int] = None
                          ):
        """ 默认查询前半个月到当天工作日中大于等于8.5的高分小说 """
        assert (start_dt and end_dt) or (start_dt is None and end_dt is None), "开始时间和结束时间错误"
        assert operator in ["eq", "gte"], "查询条件错误"

        if not ai_score:
            return []

        if start_dt is None and end_dt is None:
            now = datetime.now()
            # last_workday = RulesBase().get_previous_workday(dt=now)

            # 爬虫及AI评分工作流一般在6:30之前结束，如果用户在第二天凌时至6:30，则可能会出错误
            end_dt = datetime(year=now.year, month=now.month, day=now.day, hour=10, minute=30, second=0)
            start_dt = (end_dt - timedelta(days=15)).replace(hour=6, minute=30, second=0, microsecond=0)

        queryset = cls.query \
            .filter(
            cls.finished_time >= start_dt,
            cls.finished_time <= end_dt,
            cls.is_delete == False,
            cls.ai_score >= ai_score  # 添加过滤条件
        )

        # 直接查询并排序
        db_results = queryset.order_by(cls.pit_date.asc()).all()

        # 生成批次id
        batch_ids = [obj.batch_id for obj in db_results if obj.batch_id]
        if len(batch_ids) != len(db_results) or len(set(batch_ids)) != 1:
            # 找到其中的批次id不为空的数据
            if batch_ids:
                _batch_id = batch_ids[0]
            else:
                _batch_id = "".join(random.choices(string.ascii_letters + string.digits, k=6))

            queryset.update({"batch_id": _batch_id})
            db.session.commit()

        results = []
        existed_work_set = set()
        db_results.sort(key=attrgetter("pit_date"), reverse=True)

        if limit:
            queryset = db_results[:limit]
        else:
            queryset = db_results

        # 过滤可能有多个相同的小说
        for obj in queryset:
            key = (obj.author, obj.work_name)

            if key not in existed_work_set:
                existed_work_set.add(key)
                results.append(obj)

        return results

    @classmethod
    def get_new_work_more_by_batch_id(cls, batch_id: str):
        results = []
        existed_work_set = set()
        queryset = cls.query.filter_by(batch_id=batch_id, is_delete=False).order_by(cls.pit_date.desc()).all()

        for obj in queryset:
            key = (obj.author, obj.work_name)

            if key not in existed_work_set:
                existed_work_set.add(key)
                results.append(obj)

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
    def update_push_state_by_message_id(cls, message_id: str):
        cls.query.filter_by(message_id=message_id).update({"is_pushed": 1, "pushed_time": func.now()})
        db.session.commit()

    @classmethod
    def update_message_id_by_uniq_ids(cls, uniq_ids: List[str], message_id: str, incr: bool = False):
        cls.query.filter(cls.uniq_id.in_(uniq_ids)).update(dict(message_id=message_id))
        if incr:
            cls.query.filter(cls.uniq_id.in_(uniq_ids)).update({cls.retry_times: cls.retry_times + 1},
                                                               synchronize_session=False)
        db.session.commit()

    @classmethod
    def update_push_date_by_ids(cls, ids: List[int], push_date: str):
        cls.query.filter(cls.id.in_(ids)).update(dict(push_date=push_date))
        db.session.commit()
