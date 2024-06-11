import json
import traceback

import requests
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt

from config import settings
from wecom.core.log import logger
from wecom.bot.chatgpt_bot import ChatGPTBot
from wecom.bot.context import Context, ContextType, Reply

bot = ChatGPTBot()


def get_context(ctype, content, session_id, **kwargs) -> Context:
    context = Context(ctype, content, kwargs=kwargs)

    context["session_id"] = session_id
    context["receiver"] = session_id

    return context


@retry(stop=stop_after_attempt(max_attempt_number=settings.MAX_RETRY_TIMES))
def send_text_message(query, receiver):
    context = get_context(ctype=ContextType.TEXT, content=query, session_id=receiver)
    reply: Reply = bot.reply(query=query, context=context)

    api_path = settings.WT_API_BASE + "/wework/sendRawMessage"
    params = dict(robotId=settings.WT_ROBOTID)
    payload = dict(
        socketType=2,
        list=[
            {
                "type": 203,
                "titleList": settings.WT_GROUP_NAMES,
                "receivedContent": "@%s\n%s" % (receiver, reply.content)
            }
        ]
    )
    headers = {
        "User-Agent": UserAgent().random,
        "Content-Type": "application/json"
    }

    logger.info("send_text_message => payload: %s", payload)
    try:
        r = requests.post(api_path, params=params, data=json.dumps(payload), headers=headers)
        logger.info("send_text_message => result: %s", r.json())
    except Exception as e:
        logger.error("send_text_message error: %s", e)
        logger.error(traceback.format_exc())
