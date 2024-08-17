import json
import re
import os.path
import itertools
from operator import itemgetter, attrgetter
from datetime import timedelta, date, datetime
from typing import Dict, List, Any

from sqlalchemy import or_
from sqlalchemy.orm import load_only

# 单脚本执行时
# os.environ["APP_ENV"] = "PROD"

from scripts.base import RulesBase
from config import settings
from wecom.apps.external_groups.models.contracted_opus import ContractedOpus
from wecom.utils.log import logger
from wecom.apps.external_groups.models.script_delivery import ScriptDelivery, OutputDelivery
from wecom.apps.external_groups.models.workflowrunrecord import WorkflowRunRecord


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
        self._sync_min_ai_score = 8.4

        logger.info("SyncScriptDelivery => init workflow_id: %s, user_id: %s", self.workflow_id, self.user_id)

    @staticmethod
    def get_which_teams_from_input(input_fields: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        team_dict = {}
        mapping = {"豆瓣小说": "豆瓣", "番茄小说": "番茄", "起点小说": "起点", "晋江小说": "晋江"}

        name_list = [item["value"] for item in input_fields if item["display_name"] == "小说平台"]
        name = name_list[0] if name_list else None

        type_display_name = mapping[name] + "榜单类型" if name_list else None
        tmp_type_list = [item["value"] for item in input_fields if item["display_name"] == type_display_name]
        type_list = tmp_type_list[0] if tmp_type_list else []

        for team_items in settings.PUSH_REBOT_GROUP_MAPPING:
            team_name = team_items["name"]
            target_ai_score = team_items["target_ai_score"]

            for matching_item in team_items["matching_list"]:
                for key, values in matching_item.items():
                    if name == key:
                        if values == ["all"] or values == type_list:
                            team_dict[team_name] = dict(target_ai_score=target_ai_score)

        # logger.info("所有匹配到的团队: %s", json.dumps(team_dict, indent=4, ensure_ascii=False))
        return team_dict

    def get_matching_rids_from_output(self, output_nodes: List[Dict[str, Any]]) -> List[str]:
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

    def get_team_run_records_mapping(self) -> Dict[str, Any]:
        # team_data_dict = {ta: {"rids": [rid1, rid2], "target_ai_score": 8.4}, ......}
        team_data_dict = {}
        queryset = WorkflowRunRecord.query\
            .options(load_only(
                WorkflowRunRecord.rid,
                WorkflowRunRecord.general_details,
                WorkflowRunRecord.parent_wid
            )) \
            .filter_by(
                workflow_id=self.workflow_id,
                user_id=self.user_id, status="FINISHED"
            ) \
            .all()
        parent_objs = [obj for obj in queryset if not obj.parent_wid]

        for parent_obj in parent_objs:
            general_details = json.loads(parent_obj.general_details)
            ui_design = general_details["ui_design"]
            input_fields = ui_design["inputFields"]
            output_nodes = ui_design["outputNodes"]

            team_dict = self.get_which_teams_from_input(input_fields=input_fields)
            for team_name in team_dict:
                rids = self.get_matching_rids_from_output(output_nodes=output_nodes)

                team_item = team_data_dict.setdefault(team_name, {})
                target_ai_score = team_dict[team_name]["target_ai_score"]
                team_item["target_ai_score"] = target_ai_score
                team_item.setdefault("rids", []).extend(rids)

                logger.info("=>>> 团队: %s, target_ai_score: %s, rids: %s", team_name, target_ai_score, rids)

        return team_data_dict

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
            {"key": "ai_score", "pattern": re.compile(r"【总体评价】.*?总评分.*?(\d+\.\d)", re.S | re.M)},
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
        """ 数据入库 """
        ok_results.sort(key=itemgetter("group_name"))  # 按组名分组排序
        log_msg = "save_db ==>> 群: {group_name}, rid: {rid}, 作者: {author}, 作品: {work_name}, AI评分：{ai_score}"

        for group_name, iterator in itertools.groupby(ok_results, key=itemgetter("group_name")):
            author_books_set = set()    # 对同一个团队进行再次去除重(作者+书名)

            for item in list(iterator):
                src_url = item.get("src_url")
                author = item.get("author") or ""
                work_name = item.get("work_name") or ""
                uniq_key = author + "|" + work_name

                # 出处链接、作者、作品名必须要存在
                if author and work_name and src_url and uniq_key not in author_books_set:
                    author_books_set.add(uniq_key)

                logger.info(log_msg.format(**item))

                OutputDelivery.create(rid=item["rid"])
                ScriptDelivery.create(**item)

        # 数据落库之后，综合 T-1,T-2 等数据统一计算下一次要推送的日期(节假日不推送)
        self.compute_next_push_date()

    def compute_next_push_date(self):
        """ 计算推送日期 每个群组每天两条 """
        push_date = date.today().strftime("%Y-%m-%d")
        queryset = ScriptDelivery.query\
            .filter_by(is_pushed=False, is_delete=False)\
            .filter(or_(ScriptDelivery.push_date == "", ScriptDelivery.push_date == push_date))\
            .order_by(ScriptDelivery.group_name.asc())\
            .all()

        # 群组推送规则：开坑日期最新+评分越高的优先推送
        for group_name, iterator in itertools.groupby(queryset, key=attrgetter("group_name")):
            objects = list(iterator)
            objects.sort(key=attrgetter("pit_date", "ai_score"), reverse=True)

            # 跟新推送日期(前两条)
            ids = [obj.id for obj in objects[:2]]
            ScriptDelivery.update_push_date_by_ids(ids=ids, push_date=push_date)

            # 其他的日期置空
            other_ids = [obj.id for obj in objects[2:]]
            ScriptDelivery.update_push_date_by_ids(ids=other_ids, push_date="")

    def is_half_year(self, input_data):
        if input_data:
            pit_date = datetime.strptime(input_data, "%Y-%m-%d %H:%M:%S")
            # 获取当前日期时间
            current_date = datetime.now()
            # 计算半年前的日期时间
            half_year_ago = current_date - timedelta(days=182.5)
            if pit_date >= half_year_ago:
                return True
            else:
                return False
        else:
            return True

    def sync_records(self):
        """ 同步只在工作日同步，节假日不同步 """
        logger.info('SyncScriptDelivery.parse_records => 【开始】同步數據')

        if not self.is_workday():
            return

        ok_results = []
        team_data_mapping = self.get_team_run_records_mapping()

        for team_name, data_item in team_data_mapping.items():
            rids = data_item["rids"]
            target_ai_score = data_item["target_ai_score"]

            for run_obj in self._get_workflow_run_records(rids):
                general_details = json.loads(run_obj.general_details)
                ui_design = general_details["ui_design"]
                input_fields = ui_design["inputFields"]
                output_nodes = ui_design["outputNodes"]

                input_data = self.get_values_from_input(input_fields=input_fields)
                platform = self._get_platform(input_data.get("src_url"))
                pit_date = input_data.get("pit_date")
                is_available = self.is_half_year(pit_date)

                if is_available:
                    output_data = self.get_values_from_output(output_nodes=output_nodes)
                    values = dict(
                        rid=run_obj.rid, output="",
                        group_name=team_name, target_ai_score=target_ai_score,
                        **input_data, **output_data
                    )
                    values["platform"] = platform

                    # 重复的过滤: 只要同作者、作品和所属团队 存在的过滤
                    filter_kw = dict(group_name=team_name, author=values['author'], work_name=values["work_name"])
                    is_existed = ScriptDelivery.query.filter_by(**filter_kw).first()
                    if is_existed:
                        logger.warning("平台：{}， 团队: {group_name}, 作者：{author}, 作品: {work_name} 数据已经重复".format(platform, **filter_kw))
                        continue

                    res = ContractedOpus.query.filter_by(title=values["work_name"], author=values['author']).all()
                    logger.info(f"ContractedOpus表的查询结果为{res}")
                    if res:
                        logger.warning(f"{platform}---{values['author']}---{values['work_name']} 版权已经被采购，不进行发送")
                        continue

                    if float(values.get('ai_score', '0')) >= self._sync_min_ai_score and values.get("src_url"):
                        ok_results.append(values)
                else:
                    logger.warning(f"平台：{platform}，作者：{input_data['author']}, 作品: {input_data['work_name']}的开坑时间不在半年之内，不予推送")
        self.save_db(ok_results=ok_results)
        logger.info('SyncScriptDelivery.parse_records => 【結束】同步數據')


if __name__ == "__main__":
    from runserver import app

    with app.app_context():
        SyncScriptDeliveryRules().sync_records()

