from flask import Blueprint, request, jsonify
from flask_login import login_required

from flask import current_app

from .send import send_text_message

blueprint = Blueprint("wecom", __name__, url_prefix="/wecom", static_folder="../static")


@blueprint.route("/healthcheck")
def healthcheck():
    """ healthcheck """
    return jsonify(msg="ok", status=200, data=None)


@blueprint.route('/callback', methods=['POST'])
def callback_wecom():
    data = request.json
    current_app.logger.info("callback => data: %s", data)

    # send_text_message()


    return jsonify(msg="ok", status=200, data=None)


