import json
import string
import random
import os.path
import itertools
import traceback
from operator import itemgetter, attrgetter
from datetime import timedelta, datetime, date
from urllib.parse import urlparse, parse_qs

import requests
from sqlalchemy import text
from sqlalchemy.orm import load_only

from config import settings
from wecom.utils.log import logger
from wecom.apps.worktool.models.workflow import Workflow
from wecom.apps.worktool.models.top_author import TopAuthor, db
from wecom.apps.worktool.models.author_delivery import AuthorDelivery


class SyncAuthorRules:
    def __init__(self):
        self.max_seconds = 60 * 60 * 24

        self.workflow_id = "016bd4ad7a964addb2a91a633ab178ad"
        self.user_id = "86ab55af067944c196c2e6bc751b94f8"

    def _get_platform(self, scr_url):
        exclude_list = ["www", "com", "cn", "net"]
        domain_keywords = {
            "番茄": "fanqie",
            "起点": "qidian",
            "豆瓣": "douban",
            "晋江": "jjwxc",
        }

        ret = urlparse(scr_url)
        hostname = ret.hostname or ""
        domain_list = [s for s in hostname.split(".") if s and s not in exclude_list]

        for platform, keyword in domain_keywords.items():
            if any(keyword in d for d in domain_list):
                return platform

        return ""

    def trigger_ai_workflow(self, author, platform):
        workflow_obj = Workflow.query.options(load_only(Workflow.data)).filter_by(wid=self.workflow_id).first()
        result_proxy = db.session.execute(
            text("SELECT data FROM setting ORDER BY ID DESC LIMIT 1"),
            bind_arguments=dict(bind=db.get_engine("workflow"))
        )
        db_result = result_proxy.fetchone()
        _setting = json.loads(db_result[0])

        if workflow_obj:
            payload = {
                "user_id": self.user_id,
                "path": "workflow__run",
                "parameter": {
                    "data": {"setting": _setting,},
                    "wid": self.workflow_id,
                }
            }

            data = json.loads(workflow_obj.data)
            data['nodes'][5]['data']['template']['作者']['value'] = author
            data['nodes'][5]['data']['template']['平台名']['value'] = platform
            payload["parameter"]["data"].update(data)

            logger.info(f"工作流数据组装完成: author: {author}, platform: {platform}")

            try:
                r = requests.post(
                    "http://47.243.180.140:5000/root",
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                )
                result = r.json()
                logger.info("工作流触发结果：ret: %s", result)

                if result.get("status") == 200:
                    return result["data"]["rid"]
            except Exception as e:
                logger.error(traceback.format_exc())
        else:
            logger.error(f"workflow_id: {self.workflow_id} not found")

    def get_batch_id(self, group_name: str, push_date: str, k: int = 6):
        obj = AuthorDelivery.query\
            .options(load_only(AuthorDelivery.batch_id))\
            .filter_by(push_date=push_date, group_name=group_name)\
            .first()

        if obj is None:
            return "".join(random.choices(string.ascii_letters + string.digits, k=k))
        return obj.batch_id

    def save_db(self, ok_results: list):
        for item in ok_results:
            for group_item in settings.PUSH_REBOT_GROUP_MAPPING:
                group_name = group_item["name"]
                author = item["author"]
                work_name = item["work_name"]
                platform = item["platform"]

                # 过滤, 并且相同的工作流只执行一次
                instance = AuthorDelivery.get_object(author=author, platform=platform)
                group_instance = AuthorDelivery.get_object(author=author, work_name=work_name, group_name=group_name)

                # 获取batch_id
                push_date = date.today().strftime("%Y-%m-%d")
                batch_id = self.get_batch_id(group_name, push_date)

                if group_instance is None:
                    group_instance = AuthorDelivery.create(
                        author=author, brief=item["brief"],
                        work_name=work_name, theme=item["theme"],
                        src_url=item["src_url"], platform=platform,
                        is_pushed=False, is_workflow=False, is_delete=False,
                        group_name=group_name, finished_time=datetime.now(),
                        push_date=push_date, batch_id=batch_id
                    )

                if group_instance.workflow_state == 0:
                    # 触发工作流
                    if instance is None or not instance.rid:
                        rid = self.trigger_ai_workflow(item["author"], platform)
                        rid = rid or 0
                    else:
                        rid = instance.rid or 0

                    AuthorDelivery.update_workflow_by_id(group_instance.id, rid=rid, state=1)

    def sync_records(self):
        logger.info('SyncAuthorRules.sync_records => 【开始】同步數據')

        ok_results = []
        today = date.today()
        now_dt = datetime(year=today.year, month=today.month, day=today.day)
        queryset = TopAuthor.query\
            .filter(
                TopAuthor.create_time >= now_dt,
                TopAuthor.create_time <= now_dt.replace(hour=23, minute=59, second=59),
            )\
            .all()

        for record in queryset:
            author = record.author_name
            work_name = record.book_name

            issued_time = record.issued_time.strip() or "1979-01-01 00:00:00"
            issued_dt = datetime.strptime(issued_time, "%Y-%m-%d %H:%M:%S")

            if record.word_count.strip() == "0" or (datetime.now() - issued_dt).total_seconds() <= self.max_seconds:
                ok_results.append(dict(
                    author=author, work_name=work_name,
                    brief="", theme=record.books_type,
                    src_url=record.author_url, platform=self._get_platform(record.author_url),
                ))

        self.save_db(ok_results)
        logger.info('SyncAuthorRules.sync_records => 【結束】同步數據')


if __name__ == "__main__":
    from runserver import app

    with app.app_context():
        SyncAuthorRules().sync_records()

