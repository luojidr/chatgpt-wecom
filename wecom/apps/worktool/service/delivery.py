import re
import json
import time
import random
import threading

from config import settings, prompts
from wecom.utils.reply import MessageReply
from wecom.apps.worktool.models.workflowrunrecord import WorkflowRunRecord
from wecom.apps.worktool.models.author_delivery import AuthorDelivery
from wecom.apps.worktool.models.script_delivery import ScriptDelivery
from wecom.apps.worktool.models.rebot import RebotDetection

from wecom.utils.log import logger
from wecom.utils.enums import RebotType
from wecom.utils.template import TopAuthorNewWorkTemplate, TopAuthorNewWorkContent
from wecom.utils.template import AuthorTemplate, AuthorContentCouple, AuthorContentMore


__all__ = ["DeliveryAuthor", "DeliveryScript"]


def auto_fresh_top_author_brief():
    pattern = re.compile(r"4、.*?一句话提炼.*?市场表现等的具体亮点.*?：(.*)$", re.M | re.S)
    rid_list = AuthorDelivery.get_running_rids_by_workflow_state(workflow_state=1)
    none_text_list = [
        "由于缺乏具体的改编作品信息",
        "暂无公开信息显示",
        "暂无具体数据或奖项",
        "由于缺乏具体的数据、奖项名称等实体信息",
    ]

    for rid in rid_list:
        output_str = WorkflowRunRecord.get_output_by_rid(rid=rid)
        if output_str:
            general_details = json.loads(output_str)
            ui_design = general_details["ui_design"]
            output_nodes = ui_design["outputNodes"]

            template = output_nodes[0]["data"]["template"]
            text = template["text"]["value"]

            match = pattern.search(text)
            if match:
                brief = match.group(1).strip().lstrip(' -')
                brief = brief.split("\n", 1)[0].strip()
            else:
                if any([s in text for s in none_text_list]):
                    brief = "无"
                else:
                    continue

            AuthorDelivery.update_brief_by_rid(rid, brief, 2)


class DeliveryAuthor:
    """ 头部作者开新坑 """
    def get_templates(self):
        group_data = {}
        results = AuthorDelivery.get_required_top_author_delivery_list()

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

    def push(self):
        group_data = self.get_templates()
        for group_name, push_dict in group_data.items():
            ids = push_dict["ids"]
            batch_id = push_dict["batch_id"]
            templates = push_dict["templates"]

            if len(templates) <= 2:
                content = AuthorContentCouple(templates).get_layout_content()
            else:
                content = AuthorContentMore(templates, batch_id=batch_id).get_layout_content()

            # push_kw = dict(content=content, receiver="所有人", max_length=700)
            push_kw = dict(content=content, max_length=700)
            result = MessageReply(group_remark=group_name).simple_push(**push_kw)

            if result.get("code") == 200 and result.get("data"):
                AuthorDelivery.update_message_id_by_ids(ids, result.get("data") or "")
                time.sleep(random.randint(5, 10))


class DeliveryScript:
    def get_templates(self):
        group_data = {}
        results = ScriptDelivery.get_required_script_delivery_list()

        for group_name, objects in results.items():
            push_dict = group_data.setdefault(group_name, {})
            uniq_ids = push_dict.setdefault("uniq_ids", [])
            templates = push_dict.setdefault("templates", [])

            for obj in objects:
                templates.append(
                    TopAuthorNewWorkTemplate(
                        author=obj.author, works_name=obj.work_name,
                        theme=obj.theme, core_highlight=obj.core_highlight,
                        core_idea=obj.core_idea, platform=obj.platform,
                        pit_date=obj.pit_date, ai_score=obj.ai_score,
                        detail_url=obj.detail_url, src_url=obj.src_url
                    )
                )
                uniq_ids.append(obj.uniq_id)

        return group_data

    def push(self):
        group_data = self.get_templates()

        for group_name, push_dict in group_data.items():
            uniq_ids = push_dict.get("uniq_ids", [])
            templates = push_dict.get("templates", [])

            if uniq_ids:
                content = TopAuthorNewWorkContent(templates).get_layout_content()
                push_kw = dict(content=content, receiver="所有人", max_length=700)
                result = MessageReply(group_remark=group_name).simple_push(**push_kw)

                # eg: {'code': 200, 'message': '操作成功', 'data': True}
                if result.get("code") == 200 and result.get("data"):
                    ScriptDelivery.update_message_id_by_uniq_ids(uniq_ids, result.get("data") or "")
                    time.sleep(random.randint(5, 10))


class WTMessageListener:
    def __init__(self, callback_data):
        self.callback_data = callback_data

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

    def listen_auto_reply_to_scrcpy(self):
        """ 监听 scrcpy 的自动回复的消息 """
        message_id = self.message_state["message_id"]
        obj = RebotDetection.get_by_msg_id(msg_id=message_id, opt_type=RebotType.DETECT_SEND)

        if obj:
            RebotDetection.create(
                opt_type=RebotType.DETECT_REPLY, text="auto_reply",
                batch_seq=obj.batch_seq, msg_id=message_id,
            )

    def listen_external_group_top_author(self):
        """ 监听企微外部群(头部作者推送) """
        message_id = self.message_state["message_id"]
        AuthorDelivery.update_push_state_by_message_id(message_id)

    def listen_external_group_ai_evaluation(self):
        """ 监听企微外部群(ai评分推送) """
        message_id = self.message_state["message_id"]
        ScriptDelivery.update_push_state_by_message_id(message_id)

    def listen(self):
        message_state = self.message_state
        ai_group_names = [item["name"] for item in settings.PUSH_REBOT_GROUP_MAPPING]

        if message_state["error_code"] == 0:
            success_name = message_state["success_list"][0]

            if success_name == settings.WT_ROBOT_DETECTION_RECEIVER:
                self.listen_auto_reply_to_scrcpy()
            elif success_name in prompts.PUSH_REBOT_TOP_AUTHOR_LIST:
                self.listen_external_group_top_author()
            else:
                if success_name in ai_group_names:
                    self.listen_external_group_ai_evaluation()
        else:
            fail_name = message_state["fail_list"]

            if fail_name:
                raw_msg = message_state["raw_msg"]
                reason = message_state["error_reason"]
                logger.warn("Name: %s ==>> message failed, error_reason: %s, raw_msg: %s", fail_name, reason, raw_msg)
                logger.warn("注意: 对于发送失败的外部群信息，重新发送......")

                if fail_name in prompts.PUSH_REBOT_TOP_AUTHOR_LIST:
                    t = threading.Thread(target=DeliveryAuthor().push)
                    t.start()
                else:
                    if fail_name in ai_group_names:
                        t = threading.Thread(target=DeliveryScript().push)
                        t.start()




