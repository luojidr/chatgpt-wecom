import json
import traceback
from enum import Enum
from typing import List, Dict, Any

import requests
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt

from config import settings
from wecom.core.log import logger
from wecom.core.utils import split_long_text_by_sentences
from wecom.bot.chatgpt_bot import ChatGPTBot
from wecom.bot.context import Context, ContextType, Reply


class SendType(Enum):
    TEXT = 203
    IMG_VIDEO_FILE = 218
    EXTERNAL_GROUP = 206
    MODIFY_GROUP_INFO = 207
    UNGROUP = 219


class MessageReply:
    bot = ChatGPTBot()

    SEND_RAW_MSG_API = "/wework/sendRawMessage"
    REBOT_ONLINE_API = "/robot/robotInfo/online"

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

    def get_rebot_status(self):
        """ 检查机器人是否在线 """
        result = self.request(self.api_base + self.REBOT_ONLINE_API, method='GET')
        return result["code"] == 200 and result.get("data")

    @retry(stop=stop_after_attempt(max_attempt_number=settings.MAX_RETRY_TIMES))
    def request(self, api, payload=None, params=None, method="POST"):
        assert method in ["POST", "GET"], "request is invalid!"
        logger.info("MessageReply.%s => api: %s, payload: %s, params: %s", method.lower(), api, payload, params)

        try:
            params = params or {}
            params.update(dict(robotId=settings.WT_ROBOTID))
            kwargs = dict(params=params, headers=self.get_headers())

            if method == "POST":
                kwargs["data"] = json.dumps(payload)

            method = method.lower()
            r = requests.request(method, api, **kwargs)
            logger.info("MessageReply.%s => result: %s", method, r.json())

            return r.json()
        except Exception as e:
            logger.error("MessageReply.%s error: %s", method, e)
            logger.error(traceback.format_exc())

    def send_text(self, query, receiver):
        reply: Reply = self.get_reply(query, receiver)
        segments: List[str] = split_long_text_by_sentences(reply.content)
        text_list: List[Dict[str, Any]] = []

        for seg_text in segments:
            text_list.append(dict(
                type=SendType.TEXT.value,
                titleList=settings.WT_GROUP_NAMES,
                receivedContent="@%s\n%s" % (receiver, seg_text)
            ))

        payload = dict(socketType=2, list=text_list)
        return self.request(self.api_base + self.SEND_RAW_MSG_API, payload=payload)

    def send_file(self):
        pass


