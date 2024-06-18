import json
import re
import os.path
import logging
from urllib.parse import urlparse, parse_qs

from sqlalchemy.orm import load_only
from sqlalchemy import desc, cast, DECIMAL

# 但脚本执行时
# os.environ["APP_ENV"] = "PROD"

from config import settings
from wecom.apps.worktool.models.script_delivery import ScriptDelivery
from wecom.apps.worktool.models.workflowrunrecord import WorkflowRunRecord


class SyncScriptDelivery:
    def __init__(self, workflow_id: str = None, user_id: str = None):
        self.workflow_id = workflow_id or os.environ["SYNC_WORKFLOW_ID"]
        self.user_id = user_id or os.environ["SYNC_USER_ID"]
        self.min_ai_score = 8.3

        logging.warning("SyncScriptDelivery => init workflow_id: %s, user_id: %s", self.workflow_id, self.user_id)

    def parse_url_params(self, url):
        # 解析 URL
        parsed_url = urlparse(url)

        # 获取 URL 的 fragment 部分
        fragment = parsed_url.fragment

        # 解析 fragment 中的参数
        fragment_params = urlparse(f"//{fragment}")

        # 获取查询参数
        query_params = parse_qs(fragment_params.query)

        return query_params

    def get_which_teams_from_input(self, input_fields):
        mapping = {
            "豆瓣小说": "豆瓣",
            "番茄小说": "番茄",
            "起点小说": "起点",
        }
        team_name_set = set()

        name_list = [item["value"] for item in input_fields if item["display_name"] == "小说平台"]
        name = name_list[0] if name_list else None

        type_display_name = mapping[name] + "榜单类型" if name_list else None
        tmp_type_list = [item["value"] for item in input_fields if item["display_name"] == type_display_name]
        type_list = tmp_type_list[0] if tmp_type_list else []

        for team_items in settings.PUSH_REBOT_GROUP_MAPPING:
            team_name = team_items["name"]

            for matching_item in team_items["matching_list"]:
                for key, values in matching_item.items():
                    if (name and name == key) and (type_list and type_list == values):
                        team_name_set.add(team_name)

        logging.warning("匹配到团队: %s", team_name_set)
        return list(team_name_set)

    def get_matching_rids_from_output(self, output_nodes):
        results = []

        for output in output_nodes:
            template = output["data"]["template"]
            value_list = template["text"]["value"]

            for item in value_list:
                book_url = item.get("book_url")
                if book_url and book_url.startswith("http"):
                    rids = self.parse_url_params(book_url).get("rid")
                    if rids:
                        results.append(rids[0])

        return results

    def get_team_run_records_mapping(self):
        # {team_name: [rid1,rid2]}
        team_data = {}
        queryset = WorkflowRunRecord.query\
            .options(load_only(WorkflowRunRecord.rid, WorkflowRunRecord.general_details, WorkflowRunRecord.parent_wid)) \
            .filter_by(workflow_id=self.workflow_id, user_id=self.user_id, status="FINISHED") \
            .all()

        parent_objs = [obj for obj in queryset if not obj.parent_wid]
        for parent_obj in parent_objs:
            general_details = json.loads(parent_obj.general_details)
            ui_design = general_details["ui_design"]
            input_fields = ui_design["inputFields"]
            output_nodes = ui_design["outputNodes"]

            team_name_list = self.get_which_teams_from_input(input_fields=input_fields)
            for team_name in team_name_list:
                rids = self.get_matching_rids_from_output(output_nodes=output_nodes)
                team_data.setdefault(team_name, []).extend(rids)
                logging.warning("=>>> 团队: %s, rids: %s", team_name, rids)

        return team_data

    def is_existed(self, author, work_name, group_name):
        # 重复的过滤
        # 只要同作者、作品和所属团队 存在的就不新增
        obj = ScriptDelivery.query.filter_by(author=author, work_name=work_name, group_name=group_name).first()
        return bool(obj)

    def get_values_from_input(self, input_fields):
        data = {}

        for input_item in input_fields:
            name = input_item["name"]
            value = input_item["value"] or ""

            if name == "开坑时间":
                data["pit_date"] = value
            elif name == "出处链接":
                data["src_url"] = value
            elif name == "作者":
                data["author"] = value
            elif name == "小说名":
                data["work_name"] = value

        return data

    def get_values_from_output(self, output_nodes):
        data = {}
        long_text = ""

        for output in output_nodes[:3]:
            template = output["data"]["template"]
            text = template["text"]["value"]
            long_text += text

        # 题材类型
        theme_regex = re.compile(r"【题材类型】：(.*?)【", re.S | re.M)
        theme_match = theme_regex.search(long_text)
        if theme_match:
            theme = theme_match.group(1).strip()
            data["theme"] = theme

        # AI评分
        score_regex = re.compile(r"【总体评价】.*?总评分.*?(\d+\.\d+)", re.S | re.M)
        score_mach = score_regex.search(long_text)
        if score_mach:
            ai_score = score_mach.group(1)
            data["ai_score"] = ai_score

        # 核心亮点
        core_highlight_regex = re.compile(r"【故事Slogan】：(.*)【|【故事Solgan】：(.*)【", re.S | re.M)
        core_highlight_match = core_highlight_regex.search(long_text)
        if core_highlight_match:
            core_highlight = [s for s in core_highlight_match.groups() if s]
            data["core_highlight"] = core_highlight[0].strip()

        # 核心创意
        core_idea_regex = re.compile(r"【核心创意】：(.*)$", re.S | re.M)
        core_idea_match = core_idea_regex.search(long_text)
        if core_idea_match:
            core_idea = core_idea_match.group(1).strip()
            data["core_idea"] = core_idea

        return data

    def _get_workflow_run_records(self, rids):
        queryset = WorkflowRunRecord.query \
            .options(load_only(WorkflowRunRecord.rid, WorkflowRunRecord.general_details)) \
            .filter(WorkflowRunRecord.rid.in_(rids), WorkflowRunRecord.status == "FINISHED") \
            .all()

        return queryset

    def save_db(self, ok_results):
        # 把评分最高的数据放进表里
        ok_results.sort(key=lambda x: float(x["ai_score"]), reverse=True)

        for each_values in ok_results:
            rid = each_values["rid"]
            author = each_values["author"]
            work_name = each_values["work_name"]
            ai_score = each_values["ai_score"]
            logging.warning("rid: %s, author: %s, work_name: %s, ai_score：%s", rid, author, work_name, ai_score)

            ScriptDelivery.create(**each_values)

    def parse_records(self):
        logging.warning('SyncScriptDelivery.parse_records => 【开始】同步數據')

        ok_results = []
        team_data_mapping = self.get_team_run_records_mapping()

        for team_name, rids in team_data_mapping.items():
            for run_obj in self._get_workflow_run_records(rids):
                general_details = json.loads(run_obj.general_details)
                ui_design = general_details["ui_design"]
                input_fields = ui_design["inputFields"]
                output_nodes = ui_design["outputNodes"]

                input_data = self.get_values_from_input(input_fields=input_fields)
                output_data = self.get_values_from_output(output_nodes=output_nodes)
                values = dict(
                    rid=run_obj.rid,
                    # output=run_obj.general_details,
                    output="",
                    group_name=team_name,
                    **input_data, **output_data
                )

                filter_kw = dict(group_name=team_name, author=values['author'], work_name=values["work_name"])
                if self.is_existed(**filter_kw):
                    logging.warning("以重复的数据: %s", filter_kw)
                    continue

                if float(values.get('ai_score', '0')) >= self.min_ai_score:
                    ok_results.append(values)

        self.save_db(ok_results=ok_results)
        logging.warning('SyncScriptDelivery.parse_records => 【結束】同步數據')


if __name__ == "__main__":
    from runserver import app

    with app.app_context():
        SyncScriptDelivery(
            workflow_id="a0d1492e072a4c05893b692c4d19471e",
            user_id="86ab55af067944c196c2e6bc751b94f8"
        ).parse_records()





