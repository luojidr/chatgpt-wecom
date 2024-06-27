import time

from faker import Faker
from pyquery import PyQuery
from tenacity import retry, stop_after_attempt
from playwright.sync_api import sync_playwright

from config import settings
from .reply import MessageReply
from wecom.utils.log import logger
from wecom.utils.enums import RebotType
from wecom.apps.worktool.models.rebot import RebotDetection


@retry(stop=stop_after_attempt(max_attempt_number=3))
def is_cloud_phone_connected():
    is_connected = False

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        content = browser.new_context()
        page = content.new_page()
        page.goto("http://8.217.15.229:8010/")
        page.wait_for_timeout(3000)
        html = page.content()

        document = PyQuery(html)
        selector = '#goog_device_list #tracker_instance1 .desc-block[data-player-code-name="broadway"] a'
        text = document(selector).text()

        if not text:
            raise ValueError("可能没有获取到网页内容")

        if text.strip().lower() == "broadway.js":
            is_connected = True

        content.close()
        browser.close()

    return is_connected


def save_rebot_auto_reply(callback_data):
    message_id = callback_data.get("messageId")
    success_list = callback_data.get("successList")
    error_reason = callback_data.get("errorReason")

    if success_list and success_list[0] == settings.WT_ROBOT_DETECTION_RECEIVER:
        if error_reason is not None and len(error_reason) == 0:
            obj = RebotDetection.get_by_msg_id(msg_id=message_id, opt_type=RebotType.DETECT_SEND)
            if obj:
                RebotDetection.create(opt_type=RebotType.DETECT_REPLY, text="auto_reply", batch_seq=obj.batch_seq)


def autodetect_rebot_reply(timeout: int = 60):
    fake = Faker(locale="zh_CN")
    short_sentence: str = fake.sentence()

    query = short_sentence
    result = MessageReply().send_text(query=query, receiver=settings.WT_ROBOT_DETECTION_RECEIVER)

    if not result:
        logger.warn("机器人探测推送失败，请检查机器人是否正常")
        return

    # eg: {"code": 200, "message": "指令已加入代发队列中！", "data": "1806166646799163392"}
    result["msg_id"] = result.get("data") or ""
    instance = RebotDetection.create(opt_type=RebotType.DETECT_SEND, text=short_sentence, **result)
    msg_id = instance.msg_id
    send_timestamp = instance.timestamp

    while int(time.time()) - send_timestamp < timeout:
        obj = RebotDetection.get_by_msg_id(msg_id=msg_id, opt_type=RebotType.DETECT_REPLY)
        if obj:
            return True
        time.sleep(3)

    return False

