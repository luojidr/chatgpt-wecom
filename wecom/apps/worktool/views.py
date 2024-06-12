import os.path
from flask import send_from_directory
from flask import Blueprint, request, jsonify

from config import settings
from ...core.send import MessageReply
from ...core.log import logger
from ...bot.context import WTTextType

blueprint = Blueprint("wecom", __name__, url_prefix="/wecom", static_folder="../static")


@blueprint.route("/healthcheck")
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
    static_path = os.path.join(settings.PROJECT_PATH, "static")
    file_path = os.path.join(static_path, filename)
    logger.info("static => static_path: %s, filename: %s", static_path, filename)

    if not os.path.exists(static_path) or not os.path.exists(file_path):
        return jsonify(msg="目录或文件不存在！", status=5002, data=None)

    return send_from_directory(static_path, filename, as_attachment=True)


@blueprint.route('/callback', methods=['POST'])
def callback_wecom():
    data = request.json
    logger.info("callback => data: %s", data)

    text_type = data.get("textType", 0)
    if text_type != WTTextType.TEXT.value:
        return jsonify(msg="textType: %s not support!", status=200, data=None)

    if not data.get("rawSpoken", "").startswith(settings.WT_REBOT_NAME):
        return jsonify(msg="群聊消息！", status=200, data=None)

    query = data.get('spoken', "")
    receiver = data.get('receivedName')

    if query and receiver:
        MessageReply().send_text(query, receiver=receiver)

    return jsonify(msg="ok", status=200, data=None)


