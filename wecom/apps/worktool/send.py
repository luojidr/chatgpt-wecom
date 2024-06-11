import json
import traceback

import requests
from tenacity import retry, stop_after_attempt

from config import settings
from wecom.core.log import logger
from wecom.bot.context import Context, ContextType
from wecom.bot.chatgpt_bot import ChatGPTBot

bot = ChatGPTBot()


def get_context(ctype, content, session_id, **kwargs):
    context = Context(ctype, content, kwargs=kwargs)

    context["session_id"] = session_id
    context["receiver"] = session_id

    return context


@retry(stop=stop_after_attempt(max_attempt_number=settings.MAX_RETRY_TIMES))
def send_text_message(query, receiver):
    context = get_context(ctype=ContextType.TEXT, content=query, session_id=receiver)
    reply = bot.reply(query=query, context=context)
    is_ok, result = reply["is_ok"], reply["data"]

    if not is_ok:
        logger.warning("send_text_message => chatgpt failed: %s", result["content"])
        return

    api_path = "/wework/sendRawMessage"
    data = dict(
        socketType=2,
        list=[
            {
                "type": 203,
                "titleList": settings.WT_GROUP_NAMES,
                "receivedContent": "@%s %s" % (receiver, result["content"])
            }
        ]
    )

    try:
        requests.post(settings.WT_API_BASE + api_path, data=json.dumps(data))
    except Exception as e:
        logger.error("send_text_message error: %s", e)
        logger.error(traceback.format_exc())
