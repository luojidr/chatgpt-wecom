import json
import string
import random
import traceback
from datetime import datetime, date


import requests
from sqlalchemy import text
from sqlalchemy.orm import load_only

from scripts.base import RulesBase
from config import settings, prompts
from wecom.utils.log import logger
from wecom.apps.worktool.models.workflow import Workflow
from wecom.apps.worktool.models.workflowrunrecord import WorkflowRunRecord
from wecom.apps.worktool.models.top_author import TopAuthor, db
from wecom.apps.worktool.models.author_delivery import AuthorDelivery


class SyncAuthorRules(RulesBase):
    def __init__(self):
        self.max_seconds = 1 * 24 * 60 * 60

        self.workflow_id = "a77a8cfdf01e4ebcb57d75719e2988c9"
        self.user_id = "86ab55af067944c196c2e6bc751b94f8"

    def trigger_ai_workflow(self, author, platform):
        workflow_obj = Workflow.query\
            .options(load_only(Workflow.data))\
            .filter_by(wid=self.workflow_id, user_id=self.user_id)\
            .first()

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
                    "data": {"setting": _setting},
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

    def _get_workflow_run_record_id(self, author, platform, push_date: str):
        instance = AuthorDelivery.get_object(author=author, platform=platform, push_date=push_date)
        if instance is None or not instance.rid:
            return False

        rid = instance.rid
        run_record = WorkflowRunRecord.query\
            .options(load_only(WorkflowRunRecord.rid))\
            .filter_by(rid=rid, user_id=self.user_id, workflow_id=self.workflow_id)\
            .first()

        return run_record and run_record.rid

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
            for group_name in prompts.PUSH_REBOT_TOP_AUTHOR_LIST:
                author = item["author"]
                work_name = item["work_name"]
                platform = item["platform"]
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

                # 过滤, 并且相同的工作流只执行一次(注意：是同用户下的具体工作流的执行记录)
                rid = self._get_workflow_run_record_id(author, platform, push_date)
                if not rid:
                    # 触发工作流
                    rid = self.trigger_ai_workflow(author, platform)

                if rid:
                    AuthorDelivery.update_workflow_by_id(group_instance.id, rid=rid, state=1)

    def sync_records(self, start_dt: str = None, end_dt: str = None):
        logger.info('SyncAuthorRules.sync_records => 【开始】同步數據')

        ok_results = []

        if not start_dt and not end_dt:
            today = date.today()
            start_dt = datetime(year=today.year, month=today.month, day=today.day)
            end_dt = start_dt.replace(hour=23, minute=59, second=59)
        else:
            start_dt = datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(end_dt, "%Y-%m-%d %H:%M:%S")

        queryset = TopAuthor.query.filter(TopAuthor.create_time >= start_dt, TopAuthor.create_time <= end_dt).all()

        for record in queryset:
            author = record.author_name
            work_name = record.book_name

            issued_time = record.issued_time.strip() or "1979-01-01 00:00:00"
            issued_dt = datetime.strptime(issued_time, "%Y-%m-%d %H:%M:%S")

            # if record.word_count.strip() == "0" or (datetime.now() - issued_dt).total_seconds() <= self.max_seconds:
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

