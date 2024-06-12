from flask import Blueprint, request, jsonify

from config import settings
from ...core.send import MessageSender
from ...core.log import logger
from ...bot.context import WTTextType

blueprint = Blueprint("wecom", __name__, url_prefix="/wecom", static_folder="../static")


@blueprint.route("/healthcheck")
def healthcheck():
    """ healthcheck """
    return jsonify(msg="ok", status=200, data=None)


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
    sender = MessageSender()

    if query and receiver:
        sender.send_text_message(query, receiver=receiver)

    return jsonify(msg="ok", status=200, data=None)


