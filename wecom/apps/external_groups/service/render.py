import re
import json
import os.path
from datetime import date

from flask import request
from flask import render_template

from wecom.apps.external_groups.models.author_delivery import AuthorDelivery
from wecom.apps.external_groups.models.script_delivery import ScriptDelivery, OutputDelivery


class RenderTemplate:
    def __init__(self, template_name):
        self.template_name = template_name

    @staticmethod
    def get_node_data(output_node, regex, pos="first"):
        name = output_node["data"]["template"]["output_title"]["value"]
        string = output_node["data"]["template"]["text"]["value"]

        iter_list = list(regex.finditer(string))
        data_list = []

        for index, itor in enumerate(iter_list):
            end = itor.end()

            if index < len(iter_list) - 1:
                value = string[end: iter_list[index + 1].start()]
            else:
                value = string[end:]

            vals = value.strip().split("\n")
            vals = [s.lstrip(" -") for s in vals]

            if pos == "first":
                data_list.append(dict(title=itor.group(0), vals=vals))
            elif pos == "mid":
                data_list.append(dict(vals=[itor.group(0) + "".join(vals)]))
            elif pos == "tail":
                data_list.append(dict(vals=[itor.group(0) + s for s in vals]))

        return dict(name=name, vals=data_list)

    def get_evaluation_detail(self):
        params = request.args
        tid = params.get("tid")
        script_delivery_obj = ScriptDelivery.get_object(uniq_id=tid)
        output_str = OutputDelivery.get_output_text_by_rid(rid=script_delivery_obj.rid)

        if not script_delivery_obj or not output_str:
            return "<html>404</html>"

        input_list = []
        output = json.loads(output_str)
        input_fields = output["ui_design"]["inputFields"]
        output_nodes = output["ui_design"]["outputNodes"]

        for input_item in input_fields:
            input_list.append(dict(
                name=input_item["name"],
                text=input_item["value"],
            ))

        regex1 = re.compile(r"【(.*?)】：", re.M | re.S)
        regex2 = re.compile(r"\d\.", re.M | re.S)

        output_list = [
            self.get_node_data(output_nodes[0], regex1),
            self.get_node_data(output_nodes[1], regex2, pos="mid"),
            self.get_node_data(output_nodes[2], regex1, pos="tail"),
        ]

        return {
            "input_list": input_list,
            "output_list": output_list,
            "chat_url": f"{os.environ['CHAT_BASE_URL']}?runId={script_delivery_obj.rid}",
        }

    def get_top_author_more_detail(self):
        batch_id = request.args.get("bid")
        if not batch_id:
            return "<html>404</html>"

        queryset = AuthorDelivery.get_more_authors_by_batch_id(batch_id)
        return dict(object_list=queryset)

    def get_new_work_more_detail(self):
        batch_id = request.args.get("bid")
        if not batch_id:
            return "<html>404</html>"

        queryset = ScriptDelivery.get_new_work_more_by_batch_id(batch_id)
        return dict(object_list=queryset)

    def get_context(self):
        name = os.path.basename(self.template_name)
        meth, ext = os.path.splitext(name)
        context_meth = "get_" + meth

        if not hasattr(self, context_meth):
            raise ValueError("不存在该方法: %s", context_meth)

        return getattr(self, context_meth)()

    def render(self):
        context = self.get_context()
        return render_template(self.template_name, **context)



