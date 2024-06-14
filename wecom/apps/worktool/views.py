import re
import os.path

from flask import render_template
from flask import send_from_directory
from flask import Blueprint, request, jsonify

from config import settings
from wecom.bot.context import WTTextType
from wecom.utils.log import logger
from wecom.utils.reply import MessageReply
from wecom.utils.template import TopAuthorNewWorkTemplate, TopAuthorNewWorkContent

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
    static_path = os.path.join(settings.PROJECT_PATH, "staticfiles")
    file_path = os.path.join(static_path, filename)
    logger.info("download => static_path: %s, filename: %s", static_path, filename)

    if not os.path.exists(static_path) or not os.path.exists(file_path):
        return jsonify(msg="目录或文件不存在！", status=5002, data=None)

    return send_from_directory(static_path, filename, as_attachment=True)


@blueprint.route("/push")
def push():
    templates = [
        TopAuthorNewWorkTemplate(
            author="乔治·米勒, 乔治·米勒,乔治·米勒", works_name="《疯狂的麦克斯：,狂暴女神,狂暴女神,狂暴女神》",
            core_highlight="弗瑞奥萨", theme="科幻/动作/惊悚/冒险",
            pit_date="2023-04-02", ai_sore="6.5",
            detail_url="https://movie.douban.com/subject/34996127/",
            src_url="https://movie.douban.com/subject/34996127/"
        )
    ]
    content = TopAuthorNewWorkContent(templates).get_layout_content()
    MessageReply(group_remark="IP智能推荐机器人").simple_push(receiver="Meta", content=content)

    return jsonify(msg="ok", status=200, data=None)


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


@blueprint.route('/evaluation/detail', methods=['GET'])
def ai_evaluation_detail():
    params = request.args
    rid = params.get("rid")
    context = {}
    return render_template("wecom/daxin.html", **context)
