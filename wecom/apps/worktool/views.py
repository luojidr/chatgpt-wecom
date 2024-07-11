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
from wecom.apps.worktool.service import chat, render, delivery
from wecom.utils import scrcpy
from wecom.utils.log import logger
from wecom.utils.reply import MessageReply
from scripts.sync_author_delivery import SyncAuthorRules
from scripts.sync_script_delivery import SyncScriptDeliveryRules


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


@blueprint.route("/scrcpy-phone/is_connected")
def check_connected_to_scrcpy_phone():
    conn_state = scrcpy.check_cloud_phone_connected()
    if conn_state == 0:
        status = 200
        msg = "connected phone is normal"
    elif conn_state == 1:
        status = 6001
        msg = "scrcpy-web is restarting now"
    elif conn_state == 2:
        status = 6002
        msg = "disconnected phone"
    else:
        raise ValueError('Not Support')

    return jsonify(msg=msg, status=status, data=None)


@blueprint.route("/rebot/send/autodetect")
def autodetect_rebot_sent():
    return jsonify(msg="autodetect", status=200, data=scrcpy.autodetect_rebot_sent())


@blueprint.route("/rebot/reply/autodetect")
def autodetect_rebot_reply():
    return jsonify(msg="autodetect", status=200, data=scrcpy.autodetect_rebot_reply())


@blueprint.route("/top_author/workflow/fresh")
def fresh_top_author_brief():
    delivery.auto_fresh_top_author_brief()
    return jsonify(msg="workflow fresh", status=200, data=None)


@blueprint.route("/static/<string:filename>")
def download(filename):
    static_path = os.path.join(settings.PROJECT_PATH, "staticfiles")
    file_path = os.path.join(static_path, filename)
    logger.info("download => static_path: %s, filename: %s", static_path, filename)

    if not os.path.exists(static_path) or not os.path.exists(file_path):
        return jsonify(msg="目录或文件不存在！", status=5002, data=None)

    return send_from_directory(static_path, filename, as_attachment=True)


@blueprint.route("/push", methods=["POST"])
def push_message():
    is_online = MessageReply().get_rebot_status()
    if not is_online:
        return jsonify(msg="rebot is offline", status=5003, data=None)

    params = request.args
    push_type = params.get("push_type")
    team_name = params.get("team_name")

    assert push_type in ["ai", "top_author"], "推送类型错误"
    logger.info("push_message => path: %s, params: %s", request.path, params)

    if push_type == "ai":
        target_func = delivery.DeliveryScript().push
    else:
        group_name = prompts.WT_TEST_GROUP_NAME if team_name == "wind" else None
        target_func = delivery.DeliveryAuthor(group_name=group_name).push

    t = threading.Thread(target=target_func, args=(current_app._get_current_object(), ))
    t.start()
    return jsonify(msg="ok", status=200, data=None)


@blueprint.route('/sync_delivery_data', methods=['POST'])
def sync_delivery_data():
    params = request.args
    sync_type = params.get("sync_type")
    assert sync_type in ["ai", "top_author"], "同步数据类型错误"
    logger.info("sync_delivery_data => path: %s, params: %s", request.path, params)

    if sync_type == "ai":
        SyncScriptDeliveryRules().sync_records()
    else:
        SyncAuthorRules().sync_records()

    return jsonify(msg="sync_script_delivery is ok", status=200, data=None)


@blueprint.route('/callback', methods=['POST'])
def callback_wecom():
    # args: request.args
    # form body: request.form
    # json: request.form

    data = request.json
    logger.info("callback => data: %s", data)
    listener = delivery.WTMessageListener(callback_data=data)
    listener.listen()

    if not listener.is_next_step:
        return jsonify(msg="listen finished, no process next step!", status=200, data=None)

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
        group_master = settings.WT_GROUP_MASTER

    if not data.get("rawSpoken", "").startswith("@" + group_master):
        logger.info("callback => 未@群主不允许聊天, group_master：%s", group_master)
        return jsonify(msg="群聊消息！", status=200, data=None)

    query = data.get('spoken', "")
    receiver = data.get('receivedName')

    if query and receiver:
        _group_name = (group_remark or group_name).strip()
        MessageReply(group_remark=_group_name).send_text(query, receiver=receiver)

    return jsonify(msg="ok", status=200, data=None)


@blueprint.route('/evaluation', methods=['GET'])
def ai_evaluation_detail():
    return render.RenderTemplate("wecom/evaluation_detail.html").render()


@blueprint.route('/top_author/more', methods=['GET'])
def top_author_more_detail():
    return render.RenderTemplate("wecom/top_author_more_detail.html").render()


@blueprint.route('/new_work/more', methods=['GET'])
def new_work_more_detail():
    return render.RenderTemplate("wecom/new_work_more_detail.html").render()


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


@blueprint.route("/platform/openai/cost/download")
def platform_openai_cost():
    pass
