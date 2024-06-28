import re
import json

from wecom.utils.reply import MessageReply
from wecom.apps.worktool.models.workflowrunrecord import WorkflowRunRecord
from wecom.apps.worktool.models.author_delivery import AuthorDelivery
from wecom.apps.worktool.models.script_delivery import ScriptDelivery
from wecom.utils.template import TopAuthorNewWorkTemplate, TopAuthorNewWorkContent
from wecom.utils.template import AuthorTemplate, AuthorContentCouple, AuthorContentMore


__all__ = ["DeliveryAuthor", "DeliveryScript"]


def auto_fresh_top_author_brief():
    pattern = re.compile(r"4\..*?具体亮点.*?：(.*)$", re.M | re.S)
    rid_list = AuthorDelivery.get_running_rids_by_workflow_state(workflow_state=1)

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

            push_kw = dict(content=content, receiver="所有人", max_length=700)
            result = MessageReply(group_remark=group_name).simple_push(**push_kw)

            if result.get("code") == 200 and result.get("data"):
                AuthorDelivery.update_push_by_ids(ids)


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
                    ScriptDelivery.update_push(uniq_ids)
