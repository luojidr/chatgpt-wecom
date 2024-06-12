import json
import traceback
from enum import Enum

import requests
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt

from config import settings
from wecom.core.log import logger
from wecom.bot.chatgpt_bot import ChatGPTBot
from wecom.bot.context import Context, ContextType, Reply


class SendType(Enum):
    TEXT = 203
    IMG_VIDEO_FILE = 218
    EXTERNAL_GROUP = 206
    MODIFY_GROUP_INFO = 207
    UNGROUP = 219


class MessageSender:
    bot = ChatGPTBot()

    SEND_RAW_MSG_API = "/wework/sendRawMessage"

    def __init__(self):
        self.api_base = settings.WT_API_BASE

    def get_context(self, ctype, content, session_id, **kwargs) -> Context:
        context = Context(ctype, content, kwargs=kwargs)

        context["session_id"] = session_id
        context["receiver"] = session_id

        return context

    def get_reply(self, query: str, session_id: str):
        context = self.get_context(ctype=ContextType.TEXT, content=query, session_id=session_id)
        reply: Reply = self.bot.reply(query=query, context=context)

        return reply

    def get_headers(self):
        return {
            "User-Agent": UserAgent().random,
            "Content-Type": "application/json"
        }

    @retry(stop=stop_after_attempt(max_attempt_number=settings.MAX_RETRY_TIMES))
    def post(self, api, payload, params=None):
        logger.info("MessageSender.post => api: %s, payload: %s, params: %s", api, payload, params)

        try:
            params = params or {}
            params.update(dict(robotId=settings.WT_ROBOTID))

            r = requests.post(
                api,
                params=params,
                data=json.dumps(payload),
                headers=self.get_headers()
            )
            logger.info("MessageSender.post => result: %s", r.json())
        except Exception as e:
            logger.error("MessageSender.post error: %s", e)
            logger.error(traceback.format_exc())

    def send_text_message(self, query, receiver):
        reply: Reply = self.get_reply(query, receiver)

        payload = dict(
            socketType=2,
            list=[
                {
                    "type": SendType.TEXT.value,
                    "titleList": settings.WT_GROUP_NAMES,
                    "receivedContent": "@%s\n%s" % (receiver, reply.content)
                }
            ]
        )

        return self.post(self.api_base + self.SEND_RAW_MSG_API, payload=payload)
