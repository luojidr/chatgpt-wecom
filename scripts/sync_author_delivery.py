import re
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
from wecom.apps.worktool.models.workflow import Workflow
from wecom.apps.worktool.models.workflowrunrecord import WorkflowRunRecord
from wecom.apps.worktool.models.top_author import TopAuthor, db
from wecom.apps.worktool.models.author_retrieval import AuthorRetrieval
from wecom.apps.worktool.models.author_delivery import AuthorDelivery
from wecom.utils.log import logger
from wecom.utils.llm import AuthorRetrievalByBingSearch


class SyncAuthorRules(RulesBase):
    def __init__(self):
        self.max_seconds = 1 * 24 * 60 * 60

        self.workflow_id = "5a8c0fc1579e4ed586f007d285084223"
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

    def get_author_brief(self, author, platform):
        is_enabled, is_adapt, brief, rid = False, False, "", ""
        retrieval_obj = AuthorRetrieval.get_author_retrieval(author, platform)

        if retrieval_obj is None:
            result = AuthorRetrievalByBingSearch(author, platform).get_invoked_result_by_llm()
            uniq = result["session_id"]
            llm_content = result["content"]

            # 1) 解析brief
            brief_pattern = re.compile(r"4、.*?一句话提炼.*?市场表现等的具体亮点.*?：(.*)$", re.M | re.S)
            brief_empty_list = [
                "由于缺乏具体的改编作品信息",
                "暂无公开信息显示",
                "暂无具体数据或奖项",
                "暂无具体代表作信息",
                "由于缺乏具体的数据、奖项名称等实体信息",
            ]

            # 影视改编的
            adapt_pattern = re.compile(r"2、.*?影视改编作品的明星主演、市场表现、.*?站内热度、口碑情况.*?：(.*?)3、", re.M | re.S)
            adapt_check_regex = re.compile(r"①《.*?》：.*?明星主演.*?市场表现.*?站内热度.*?口碑情况", re.M | re.S)

            brief_match = brief_pattern.search(llm_content)
            if brief_match:
                brief = brief_match.group(1).strip().lstrip(' -')
                brief = brief.split("\n", 1)[0].strip()

                if any([s in brief for s in brief_empty_list]):
                    is_enabled = False
                else:
                    is_enabled = True
            else:
                is_enabled, brief = False, ""

            adapt_match = adapt_pattern.search(llm_content)
            if adapt_match and adapt_check_regex.search(adapt_match.group(1)):
                is_adapt = True

            # 2) 将大模型调用bingsearch的结果入库
            retrieval_obj = AuthorRetrieval.create(
                author=author, platform=platform,
                uniq=uniq, is_enabled=is_enabled,
                brief=brief, is_adapt=is_adapt,
                bing_results=json.dumps(result["bing_results"]),
                llm_content=llm_content, is_delete=not is_enabled
            )

        return dict(
            is_enabled=retrieval_obj.is_enabled, is_adapt=retrieval_obj.is_adapt,
            brief=retrieval_obj.brief, rid=retrieval_obj.uniq
        )

    def _get_workflow_run_record_id(self, author, platform):
        # 可能之前跑出的工作流，并没有获取到【作者简介】
        instance = AuthorDelivery.query\
            .filter_by(author=author, platform=platform)\
            .filter(AuthorDelivery.rid != '')\
            .order_by(AuthorDelivery.id.asc())\
            .first()

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
        # 头部作者全部推送，当天同步数据，当天推送
        push_date = date.today().strftime("%Y-%m-%d")

        for item in ok_results:
            for group_name in prompts.PUSH_REBOT_TOP_AUTHOR_LIST:
                author = item["author"]
                work_name = item["work_name"]
                platform = item["platform"]
                group_instance = AuthorDelivery.get_object(author=author, work_name=work_name, group_name=group_name)

                # 获取batch_id
                batch_id = self.get_batch_id(group_name, push_date)

                if group_instance is None:
                    llm_result = self.get_author_brief(author, platform)

                    group_instance = AuthorDelivery.create(
                        author=author, brief=llm_result["brief"],
                        work_name=work_name, theme=item["theme"],
                        src_url=item["src_url"], platform=platform,
                        is_pushed=False,
                        group_name=group_name, finished_time=datetime.now(),
                        push_date=push_date, batch_id=batch_id,
                        rid=llm_result["rid"], workflow_state=2,
                        is_adapt=llm_result["is_adapt"], is_delete=not llm_result["is_enabled"],
                    )

                    log_args = (group_name, platform, author, work_name)
                    logger.info("团队: %s, 平台: %s, 作者: %s, 作品: %s 已完成同步并入库", *log_args)

                # # 过滤, 并且相同的工作流只执行一次(注意：是同用户下的具体工作流的执行记录)
                # rid = self._get_workflow_run_record_id(author, platform)
                # if not rid:
                #     # 触发工作流
                #     rid = self.trigger_ai_workflow(author, platform)
                #
                # if rid:
                #     AuthorDelivery.update_workflow_by_id(group_instance.id, rid=rid, state=1)

    def sync_records(self, start_dt: str = None, end_dt: str = None):
        """ 同步只在工作日同步，节假日不同步 (指定 start_dt 与 end_dt除外) """
        logger.info('SyncAuthorRules.sync_records => 【开始】同步數據')

        ok_results = []

        if not start_dt and not end_dt:
            if not self.is_workday():
                return

            now_dt = datetime.now()
            previous_date = self.get_previous_workday(now_dt)

            start_dt = datetime(year=previous_date.year, month=previous_date.month, day=previous_date.day)
            end_dt = now_dt.replace(hour=23, minute=59, second=59)

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

