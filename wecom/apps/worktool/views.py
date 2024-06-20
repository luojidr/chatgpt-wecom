import json
import re
import os.path

# from flask_login import login_required, login_user
from flask import render_template
from flask import send_from_directory
from flask import Blueprint, request, jsonify
from flask import Response, stream_with_context
# from flask_security import login_required

from config import settings
from wecom.bot.context import WTTextType
from wecom.apps.worktool.models.script_delivery import ScriptDelivery
from wecom.utils.log import logger
from wecom.utils.reply import MessageReply
from wecom.utils.template import TopAuthorNewWorkTemplate, TopAuthorNewWorkContent
from scripts.sync_script_delivery import SyncScriptDeliveryRules
from wecom.apps.worktool.service import chat

blueprint = Blueprint("wecom", __name__, url_prefix="/wecom", static_folder="../static")


@blueprint.route("/healthcheck")
# @login_required
def healthcheck():
    """ healthcheck """
    return jsonify(msg="ok", status=200, data=None)


@blueprint.route("/robot/status/check")
def check_robot_status():
    is_online = MessageReply().get_rebot_status()
    if is_online:
        return jsonify(msg="rebot is online", status=200, data=None)
    return jsonify(msg="rebot is offline", status=5001, data=None)


@blueprint.route("/static/<string:filename>")
def download(filename):
    static_path = os.path.join(settings.PROJECT_PATH, "staticfiles")
    file_path = os.path.join(static_path, filename)
    logger.info("download => static_path: %s, filename: %s", static_path, filename)

    if not os.path.exists(static_path) or not os.path.exists(file_path):
        return jsonify(msg="目录或文件不存在！", status=5002, data=None)

    return send_from_directory(static_path, filename, as_attachment=True)


@blueprint.route("/push", methods=["POST"])
def push():
    is_online = MessageReply().get_rebot_status()
    if not is_online:
        return jsonify(msg="rebot is offline", status=5003, data=None)

    results = ScriptDelivery.get_required_script_delivery_list()

    for group_name, objects in results.items():
        templates = []
        uniq_ids = []

        for obj in objects:
            templates.append(
                TopAuthorNewWorkTemplate(
                    author=obj.author, works_name=obj.work_name,
                    theme=obj.theme, core_highlight=obj.core_highlight,
                    core_idea=obj.core_idea,
                    pit_date=obj.pit_date, ai_score=obj.ai_score,
                    detail_url=obj.detail_url, src_url=obj.src_url
                )
            )
            uniq_ids.append(obj.uniq_id)

        if uniq_ids:
            ScriptDelivery.update_push(uniq_ids)

            content = TopAuthorNewWorkContent(templates).get_layout_content()
            MessageReply(group_remark=group_name).simple_push(content=content, receiver="所有人", max_length=700)

    return jsonify(msg="ok", status=200, data=None)


@blueprint.route('/sync_script_delivery', methods=['POST'])
def sync_script_delivery():
    SyncScriptDeliveryRules().parse_records()
    return jsonify(msg="sync_script_delivery is ok", status=200, data=None)


@blueprint.route('/callback', methods=['POST'])
def callback_wecom():
    # args: request.args
    # form body: request.form
    # json: request.form

    data = request.json
    logger.info("callback => data: %s", data)

    text_type = data.get("textType", 0)
    if text_type != WTTextType.TEXT.value:
        return jsonify(msg="textType: %s not support!", status=200, data=None)

    group_name = data.get("groupName", "")
    group_remark = data.get("groupRemark", "")
    logger.info("group_name: %s, group_remark: %s", group_name, group_remark)

    match = re.compile(r"群主:(.*?)$").search(group_name)
    if match is not None:
        group_master = match.group(1).strip()
    else:
        return jsonify(msg="未获取到群主！", status=200, data=None)

    if not data.get("rawSpoken", "").startswith("@" + group_master):
        return jsonify(msg="群聊消息！", status=200, data=None)

    query = data.get('spoken', "")
    receiver = data.get('receivedName')

    if query and receiver:
        MessageReply(group_remark=group_remark).send_text(query, receiver=receiver)

    return jsonify(msg="ok", status=200, data=None)


@blueprint.route('/evaluation', methods=['GET'])
def ai_evaluation_detail():
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

    params = request.args
    tid = params.get("tid")
    script_delivery_obj = ScriptDelivery.get_object(uniq_id=tid)
    output_str = ScriptDelivery.get_output_by_uniq_id(uniq_id=tid)

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
        get_node_data(output_nodes[0], regex1),
        get_node_data(output_nodes[1], regex2, pos="mid"),
        get_node_data(output_nodes[3], regex1, pos="tail"),
    ]

    context = {
        "input_list": input_list,
        "output_list": output_list,
        "chat_url": f"{os.environ['CHAT_BASE_URL']}?runId={script_delivery_obj.rid}",
    }
    return render_template("wecom/evaluation_detail.html", **context)


@blueprint.route("/v1/chat/completions", methods=['POST'])
def chat_completions():
    """ chatgpt-next-web 项目 """
    data = request.json
    messages = data["messages"]
    rid = data.get("runId", "")
    logger.info("chat_completions => rid: %s, messages: %s", rid, messages)

    chat_kwargs = dict(session_id=rid, messages=messages)
    return Response(
        stream_with_context(chat.ChatCompletion(**chat_kwargs).stream_generator()),
        content_type='text/event-stream'
    )
