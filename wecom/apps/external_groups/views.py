import re
import os.path
import threading

# from flask_login import login_required, login_user
from flask import render_template
from flask import send_from_directory
from flask import Blueprint, request, jsonify
from flask import Response, stream_with_context
from flask import current_app
# from flask_security import login_required

from config import settings, prompts
from wecom.bot.context import WTTextType
from wecom.apps.external_groups.service import chat, render, delivery
from wecom.utils.log import logger
from wecom.utils.reply import MessageReply


blueprint = Blueprint("wecom", __name__, url_prefix="/wecom", static_folder="../static")


@blueprint.route("/healthcheck")
# @login_required
def healthcheck():
    """ healthcheck """
    return jsonify(msg="ok", status=200, data=None)


@blueprint.route("/static/<string:filename>")
def download(filename):
    static_path = os.path.join(settings.PROJECT_PATH, "staticfiles")
    file_path = os.path.join(static_path, filename)
    logger.info("download => static_path: %s, filename: %s", static_path, filename)

    if not os.path.exists(static_path) or not os.path.exists(file_path):
        return jsonify(msg="目录或文件不存在！", status=5002, data=None)

    return send_from_directory(static_path, filename, as_attachment=True)


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
        is_group = True
        group_master = match.group(1).strip()
    else:
        is_group = False
        group_master = settings.WT_GROUP_MASTER

    if is_group and not data.get("rawSpoken", "").startswith("@" + group_master):
        logger.info("callback => 未@群主不允许聊天, group_master：%s", group_master)
        return jsonify(msg="群聊消息！", status=200, data=None)

    query = data.get('spoken', "")
    receiver = data.get('receivedName')

    if query and receiver:
        _group_name = (group_remark or group_name).strip()
        MessageReply(group_remark=_group_name).send_text(query, receiver=receiver)

    return jsonify(msg="ok", status=200, data=None)


@blueprint.route("/v1/chat/completions", methods=['POST'])
def chat_completions():
    """ chatgpt-next-web 项目 """
    data = request.json
    messages = data["messages"]
    rid = data.get("runId", "")

    chat_kwargs = dict(session_id=rid, messages=messages)
    return Response(
        stream_with_context(chat.ChatCompletion(**chat_kwargs).stream_generator()),
        content_type='text/event-stream'
    )
