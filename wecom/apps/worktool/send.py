import json
import traceback

import requests
from tenacity import retry, stop_after_attempt

from config import settings
from wecom.core.log import logger
from wecom.bot.chatgpt_bot import ChatGPTBot

bot = ChatGPTBot()


@retry(stop=stop_after_attempt(max_attempt_number=settings.MAX_RETRY_TIMES))
def send_text_message(reply_content):
    api_path = "/wework/sendRawMessage"
    data = dict(
        socketType=2,
        list=[
            {
                "type": 203,
                "titleList": settings.WT_GROUP_NAMES,
                "receivedContent": reply_content
            }
        ]
    )

    try:
        requests.post(settings.WT_API_BASE + api_path, data=json.dumps(data))
    except Exception as e:
        logger.error("send_text_message error: %s", e)
        logger.error(traceback.format_exc())
