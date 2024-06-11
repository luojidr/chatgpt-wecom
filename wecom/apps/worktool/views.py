from flask import Blueprint, request, jsonify
from flask_login import login_required

from .send import send_text_message
from ...core.log import logger

blueprint = Blueprint("wecom", __name__, url_prefix="/wecom", static_folder="../static")


@blueprint.route("/healthcheck")
def healthcheck():
    """ healthcheck """
    return jsonify(msg="ok", status=200, data=None)


@blueprint.route('/callback', methods=['POST'])
def callback_wecom():
    data = request.json
    logger.info("callback => data: %s", data)
    query = data.get('spoken')
    receiver = data.get('receivedName')

    if query and receiver:
        send_text_message(query, receiver=receiver)

    return jsonify(msg="ok", status=200, data=None)


