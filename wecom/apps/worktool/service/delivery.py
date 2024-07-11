import re
import json
import time
import random
import threading
from datetime import date, datetime, timedelta

from flask import current_app

from config import settings, prompts
from wecom.utils.reply import MessageReply
from wecom.apps.worktool.models.workflowrunrecord import WorkflowRunRecord
from wecom.apps.worktool.models.author_delivery import AuthorDelivery
from wecom.apps.worktool.models.script_delivery import ScriptDelivery
from wecom.apps.worktool.models.rebot import RebotDetection

from wecom.utils.log import logger
from wecom.utils.template import NewWorkTemplate, NewWorkContent, NewWorkContentMore
from wecom.utils.template import AuthorTemplate, AuthorContentCouple, AuthorContentMore


__all__ = ["DeliveryAuthor", "DeliveryScript"]


def auto_fresh_top_author_brief():
    brief_pattern = re.compile(r"4、.*?一句话提炼.*?市场表现等的具体亮点.*?：(.*)$", re.M | re.S)
    rid_list = AuthorDelivery.get_running_rids_by_workflow_state(workflow_state=1)
    brief_empty_list = [
        "由于缺乏具体的改编作品信息",
        "暂无公开信息显示",
        "暂无具体数据或奖项",
        "由于缺乏具体的数据、奖项名称等实体信息",
    ]

    # 影视改编的
    adapt_pattern = re.compile(r"2、.*?影视改编作品的明星主演、市场表现、.*?站内热度、口碑情况.*?：(.*?)3、", re.M | re.S)
    adapt_check_regex = re.compile(r"①《.*?》：.*?明星主演.*?市场表现.*?站内热度.*?口碑情况", re.M | re.S)

    for rid in rid_list:
        output_str = WorkflowRunRecord.get_output_by_rid(rid=rid)
        if output_str:
            general_details = json.loads(output_str)
            ui_design = general_details["ui_design"]
            output_nodes = ui_design["outputNodes"]

            template = output_nodes[0]["data"]["template"]
            text = template["text"]["value"]

            if any([s in text for s in brief_empty_list]):
                upt_value = dict(rid="", brief="", is_delete=True, workflow_state=2)
            else:
                brief_match = brief_pattern.search(text)
                if brief_match:
                    brief = brief_match.group(1).strip().lstrip(' -')
                    brief = brief.split("\n", 1)[0].strip()

                    upt_value = dict(brief=brief, is_delete=False, workflow_state=2)
                else:
                    upt_value = dict(rid="", brief="", is_delete=True, workflow_state=2)

            adapt_match = adapt_pattern.search(text)
            if adapt_match and adapt_check_regex.search(adapt_match.group(1)):
                upt_value.update(is_adapt=True)

            AuthorDelivery.update_value_by_rid(rid, upt_value)


class DeliveryAuthor:
    """ 头部作者开新坑 """
    def __init__(self, group_name: str = None):
        self._group_name = group_name

    def get_templates(self):
        group_data = {}
        results = AuthorDelivery.get_required_top_author_delivery_list(self._group_name)

        for group_name, objects in results.items():
            push_dict = group_data.setdefault(group_name, {})
            push_dict["batch_id"] = objects[0].batch_id

            ids = push_dict.setdefault("ids", [])
            templates = push_dict.setdefault("templates", [])

            for obj in objects:
                ids.append(obj.id)
                templates.append(
                    AuthorTemplate(
                        author=obj.author, works_name=obj.work_name,
                        theme=obj.theme, platform=obj.platform,
                        brief=obj.brief, src_url=obj.src_url
                    )
                )

        return group_data

    def push(self, app, incr: bool = False):
        time.sleep(random.randint(4, 10))

        with app.app_context():
            group_data = self.get_templates()

            for group_name, push_dict in group_data.items():
                ids = push_dict["ids"]
                batch_id = push_dict["batch_id"]
                templates = push_dict["templates"]

                # 注意：[头部作者开新坑]有影视改编作品的，放在最前位置

                if len(templates) <= 2:
                    content = AuthorContentCouple(templates).get_layout_content()
                else:
                    content = AuthorContentMore(templates, batch_id=batch_id).get_layout_content()

                # push_kw = dict(content=content, receiver="所有人", max_length=700)
                push_kw = dict(content=content, max_length=700)
                result = MessageReply(group_remark=group_name).simple_push(**push_kw)

                if result.get("code") == 200 and result.get("data"):
                    AuthorDelivery.update_message_id_by_ids(ids, result.get("data") or "", incr=incr)
                    time.sleep(random.randint(5, 10))


class DeliveryScript:
    """ ai评分 """
    def __init__(self, group_name: str = None):
        self._group_name = group_name

    def _get_template_data(self, obj):
        return dict(
            author=obj.author, works_name=obj.work_name,
            theme=obj.theme, core_highlight=obj.core_highlight,
            core_idea=obj.core_idea, platform=obj.platform,
            pit_date=obj.pit_date, ai_score=obj.ai_score,
            detail_url=obj.detail_url, src_url=obj.src_url
        )

    def get_templates(self):
        group_data = {}
        results = ScriptDelivery.get_required_script_delivery_list(self._group_name)

        for group_name, objects in results.items():
            push_dict = group_data.setdefault(group_name, {})
            uniq_ids = push_dict.setdefault("uniq_ids", [])
            templates = push_dict.setdefault("templates", [])

            for obj in objects:
                templates.append(NewWorkTemplate(**self._get_template_data(obj)))
                uniq_ids.append(obj.uniq_id)

        return group_data

    def push(self, app, g_name: str = None, incr: bool = False):
        time.sleep(random.randint(4, 10))

        with app.app_context():
            group_data = self.get_templates()

            for group_name, push_dict in group_data.items():
                uniq_ids = push_dict.get("uniq_ids", [])
                templates = push_dict.get("templates", [])

                if uniq_ids:
                    content = NewWorkContent(templates).get_layout_content()
                    push_kw = dict(content=content, receiver="所有人", max_length=700)
                    result = MessageReply(group_remark=group_name).simple_push(**push_kw)

                    # eg: {'code': 200, 'message': '操作成功', 'data': True}
                    if result.get("code") == 200 and result.get("data"):
                        ScriptDelivery.update_message_id_by_uniq_ids(uniq_ids, result.get("data") or "", incr=incr)
                        time.sleep(random.randint(5, 10))

    def push_by_high_score(self, group_name: str, receiver: str, ai_score: float = 8.5, limit: int = None):
        # 查询当天同步(24小时以内)的推送的高分小说
        today = date.today()
        start_dt = datetime(year=today.year, month=today.month, day=today.day) - timedelta(days=1)
        end_dt = datetime(year=today.year, month=today.month, day=today.day, hour=10, minute=0, second=0)

        queryset = ScriptDelivery.query_by_ai_score(start_dt=start_dt, end_dt=end_dt, ai_score=ai_score, limit=limit)
        templates = [NewWorkTemplate(**self._get_template_data(obj)) for obj in queryset]

        if not templates:
            content = f"喔！目前没有{ai_score}分的IP推荐给您。"
        else:
            content = NewWorkContentMore(
                templates, batch_id=queryset[0].batch_id, target_score=ai_score
            ).get_layout_content()

        return MessageReply(group_remark=group_name).simple_push(content=content, receiver=receiver, max_length=700)


class WTMessageListener:
    def __init__(self, callback_data):
        self.callback_data = callback_data
        self.is_next_step = True

    @property
    def message_state(self):
        error_code = self.callback_data.get("errorCode")
        message_id = self.callback_data.get("messageId")
        fail_list = self.callback_data.get("failList")
        success_list = self.callback_data.get("successList")
        error_reason = self.callback_data.get("errorReason")

        return dict(
            error_code=error_code, error_reason=error_reason,
            success_list=success_list, message_id=message_id,
            fail_list=fail_list, raw_msg=self.callback_data.get("rawMsg")
        )

    @property
    def message_id(self):
        return self.message_state["message_id"]

    def listen_auto_reply_to_scrcpy(self):
        """ 监听 scrcpy 的自动回复的消息 """
        RebotDetection.update_reply_ok_by_msg_id(msg_id=self.message_id)
        self.is_next_step = False

    def listen_external_group_top_author_by_api(self):
        """ 监听企微外部群(头部作者推送) """
        AuthorDelivery.update_push_state_by_message_id(self.message_id)
        self.is_next_step = False

    def listen_external_group_ai_evaluation_by_api(self):
        """ 监听企微外部群(ai评分推送) """
        ScriptDelivery.update_push_state_by_message_id(self.message_id)
        self.is_next_step = False

    def listen_external_group_ip_by_chat(self, target_score: float = 8.5):
        """ 监听企微外部群的聊天(高分IP推荐), 并推送信息 """
        # Sample: {
        #     'groupName': '机器人测试群', 'fileName': '', 'atMe': 'true', 'filePath': '', 'groupRemark': '',
        #     'spoken': '8.5', 'textType': 1, 'rawSpoken': '@小风机器人\u20058.5', 'receivedName': 'Derek', 'roomType': 1
        # }
        digit_pattern = re.compile(r"^\d+\.\d+$")

        if self.callback_data.get("roomType") == 1:
            group_name = self.callback_data.get("groupName")
            receiver = self.callback_data.get("receivedName")
            raw_spoken = self.callback_data.get("rawSpoken") or ""

            if not raw_spoken.startswith("@" + settings.WT_GROUP_MASTER):
                return

            query = raw_spoken.replace("@" + settings.WT_GROUP_MASTER, "").strip()

            if digit_pattern.match(query) and float(query) == target_score:
                if group_name:
                    DeliveryScript().push_by_high_score(group_name=group_name, receiver=receiver, ai_score=target_score)
                    self.is_next_step = False

    def listen(self):
        message_state = self.message_state
        error_code = message_state["error_code"]
        ai_group_names = [item["name"] for item in settings.PUSH_REBOT_GROUP_MAPPING]

        if error_code is None:
            self.listen_external_group_ip_by_chat()
        elif error_code == 0:
            success_list = message_state["success_list"]
            if not success_list:
                return

            success_name = success_list[0]
            logger.warn("恭喜，群：[%s] 发送消息成功，消息ID: %s", success_name, self.message_id)

            if success_name == settings.WT_ROBOT_DETECTION_RECEIVER:
                self.listen_auto_reply_to_scrcpy()
            else:
                # message_id 肯定不一样的
                if success_name in prompts.PUSH_REBOT_TOP_AUTHOR_LIST:
                    self.listen_external_group_top_author_by_api()

                if success_name in ai_group_names:
                    self.listen_external_group_ai_evaluation_by_api()
        else:
            target_func = None
            fail_list = message_state["fail_list"]
            app = current_app._get_current_object()

            if fail_list:
                fail_name = fail_list[0]
                reason = message_state["error_reason"]

                if fail_name in prompts.PUSH_REBOT_TOP_AUTHOR_LIST:
                    target_func = DeliveryAuthor(group_name=fail_name).push
                else:
                    if fail_name in ai_group_names:
                        target_func = DeliveryScript(group_name=fail_name).push

                if target_func:
                    logger.warn("哎吆，群: [%s] 发送消息失败, 原因: %s, 消息ID: %s", fail_name, reason, self.message_id)
                    logger.warn("注意: 对于发送失败的外部群信息，重新发送......\n\n")

                    # 只对自己的群组进行补偿推送
                    t = threading.Thread(target=target_func, args=(app, True))
                    t.start()



