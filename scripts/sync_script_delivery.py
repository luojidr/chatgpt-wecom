import json
import re
import os.path
import itertools
from operator import itemgetter
from datetime import timedelta

from sqlalchemy.orm import load_only

# 单脚本执行时
# os.environ["APP_ENV"] = "PROD"

from scripts.base import RulesBase
from config import settings
from wecom.utils.log import logger
from wecom.apps.worktool.models.script_delivery import ScriptDelivery, OutputDelivery
from wecom.apps.worktool.models.workflowrunrecord import WorkflowRunRecord


class SyncScriptDeliveryRules(RulesBase):
    """ 同步规则：
    1) 推送团队: team1, team2, team2, ......
    2) 按照每个团队的规则进行数据匹配：如 team1 匹配数据 n1 条，team1 匹配数据 n2 条；每个团队的数据可能有交集。
    3) 推送条数控制：每个团队最多只匹配2条，目前各个团队各退各的，即使数据有交集。
    4) 同步数量控制：每日同步按评分最高的取前两条，每个团队有就推送，没有就不推送。
    5) 如果 team1 匹配了5条，那么当天退了2调后，其他的3条T+1,T+2接着推，如此反复
    """

    def __init__(self, workflow_id: str = None, user_id: str = None):
        self.workflow_id = workflow_id or os.environ["SYNC_WORKFLOW_ID"]
        self.user_id = user_id or os.environ["SYNC_USER_ID"]
        self.min_ai_score = 8.5

        logger.info("SyncScriptDelivery => init workflow_id: %s, user_id: %s", self.workflow_id, self.user_id)

    @staticmethod
    def get_which_teams_from_input(input_fields):
        team_name_set = set()
        mapping = {"豆瓣小说": "豆瓣", "番茄小说": "番茄", "起点小说": "起点"}

        name_list = [item["value"] for item in input_fields if item["display_name"] == "小说平台"]
        name = name_list[0] if name_list else None

        type_display_name = mapping[name] + "榜单类型" if name_list else None
        tmp_type_list = [item["value"] for item in input_fields if item["display_name"] == type_display_name]
        type_list = tmp_type_list[0] if tmp_type_list else []

        for team_items in settings.PUSH_REBOT_GROUP_MAPPING:
            team_name = team_items["name"]

            for matching_item in team_items["matching_list"]:
                for key, values in matching_item.items():
                    if name == key and type_list == values:
                        team_name_set.add(team_name)

        logger.info("匹配到团队: %s", team_name_set)
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
        # team_data = {team_name1: [rid1, rid2], team_name2: [rid3, rid4], ......}
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
                logger.info("=>>> 团队: %s, rids: %s", team_name, rids)

        return team_data

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
        pattern_list = [
            # 题材类型
            {"key": "theme", "pattern": re.compile(r"【题材类型】：(.*?)【", re.S | re.M)},
            # AI评分
            {"key": "ai_score", "pattern": re.compile(r"【总体评价】.*?总评分.*?(\d+\.\d+)", re.S | re.M)},
            # 核心亮点
            {"key": "core_highlight", "pattern": re.compile(r"【故事Slogan】：(.*)【|【故事Solgan】：(.*)【", re.S | re.M)},
            # 核心创意
            {"key": "core_idea", "pattern": re.compile(r"【核心创意】：(.*)$", re.S | re.M)},
        ]

        for output in output_nodes[:3]:
            template = output["data"]["template"]
            text = template["text"]["value"]
            long_text += text

        for item in pattern_list:
            key, pattern = item["key"], item["pattern"]
            match = pattern.search(long_text)
            if match:
                values = [s.strip() for s in match.groups() if s]
                data[key] = values[0]

        return data

    def _get_workflow_run_records(self, rids):
        queryset = WorkflowRunRecord.query \
            .options(load_only(WorkflowRunRecord.rid, WorkflowRunRecord.general_details)) \
            .filter(WorkflowRunRecord.rid.in_(rids), WorkflowRunRecord.status == "FINISHED") \
            .all()

        return queryset

    def save_db(self, ok_results):
        step = 2
        ok_results.sort(key=itemgetter("group_name"))  # 按组名分组排序
        log_msg = "save_db ==>> group_name: %s, push_date: %s, rid: %s, author: %s, work_name: %s, ai_score：%s"

        for group_name, iterator in itertools.groupby(ok_results, key=itemgetter("group_name")):
            # 再次去除重复的数据(作者+书名)
            values = []
            author_books_set = set()

            for item in list(iterator):
                src_url = item.get("src_url")
                author = item.get("author") or ""
                work_name = item.get("work_name") or ""
                uniq_key = author + "|" + work_name

                # 出处链接、作者、作品名必须要存在
                if author and work_name and src_url and uniq_key not in author_books_set:
                    author_books_set.add(uniq_key)
                    values.append(item)

            # 计算 push_date
            is_new, push_date = ScriptDelivery.get_latest_push_date_by_group_name(group_name)
            tmp_push_date = push_date - timedelta(days=1)

            # 每 step 个分组
            group_values = []
            if not is_new and values:
                group_values.append([values.pop(0)])
            group_values.extend([values[i:i + step] for i in range(0, len(values), step)])

            for each_values in group_values:
                tmp_push_date = tmp_push_date + timedelta(days=1)
                # 周末不推
                while tmp_push_date.weekday() in [5, 6]:
                    tmp_push_date = tmp_push_date + timedelta(days=1)

                push_date_str = tmp_push_date.strftime("%Y-%m-%d")
                # print(group_name, each_item["author"], each_item["work_name"])

                for each_item in each_values:
                    rid = each_item["rid"]
                    each_item["push_date"] = push_date_str

                    log_args = (
                        group_name, push_date_str, rid,
                        each_item["author"], each_item["work_name"], each_item["ai_score"]
                    )
                    logger.info(log_msg, *log_args)
                    OutputDelivery.create(rid=rid)
                    ScriptDelivery.create(**each_item)

    def sync_records(self):
        logger.info('SyncScriptDelivery.parse_records => 【开始】同步數據')

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
                    rid=run_obj.rid, output="",
                    # output=run_obj.general_details,
                    group_name=team_name,
                    **input_data, **output_data
                )

                # 重复的过滤: 只要同作者、作品和所属团队 存在的就不新增
                filter_kw = dict(group_name=team_name, author=values['author'], work_name=values["work_name"])
                is_existed = ScriptDelivery.query.filter_by(**filter_kw).first()
                if is_existed:
                    logger.info("以重复的数据: %s", filter_kw)
                    continue

                # 计算小说所属平台
                values["platform"] = self._get_platform(values.get("src_url"))

                if float(values.get('ai_score', '0')) >= self.min_ai_score:
                    ok_results.append(values)

        self.save_db(ok_results=ok_results)
        logger.info('SyncScriptDelivery.parse_records => 【結束】同步數據')


if __name__ == "__main__":
    from runserver import app

    with app.app_context():
        SyncScriptDeliveryRules(
            workflow_id="5a5972201eb4432ca9dfb434d3b4a931",
            user_id="86ab55af067944c196c2e6bc751b94f8"
        ).sync_records()

