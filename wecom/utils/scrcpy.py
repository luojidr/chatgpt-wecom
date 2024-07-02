import time
import traceback
from datetime import datetime

from faker import Faker
from pyquery import PyQuery
from tenacity import retry, stop_after_attempt
from playwright.sync_api import sync_playwright, Error

from config import settings
from .reply import MessageReply
from wecom.utils.log import logger
from wecom.utils.enums import RebotType
from wecom.apps.worktool.models.rebot import RebotDetection


@retry(stop=stop_after_attempt(max_attempt_number=3))
def check_cloud_phone_connected():
    """ 分2步 1) scrcpy-web 正常运行 2) 能够正常连接云手机 """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        content = browser.new_context()
        page = content.new_page()

        try:
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
        except Error as e1:
            # scrcpy-web 可能没有呢正常运行(scrcpy-web是 dokcer 会自启动)
            logger.error("Maybe load url err: %s", e1)
            return 1
        except Exception as e2:
            # 可能没有正常连接云手机
            logger.error("Maybe other err: %s", e2)
            logger.error(traceback.format_exc())
            return 2
        finally:
            content.close()
            browser.close()

    return 0


def autodetect_rebot_sent():
    fake = Faker(locale="zh_CN")
    short_sentence: str = fake.sentence()

    receiver = settings.WT_ROBOT_DETECTION_RECEIVER
    query = "[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), short_sentence)
    result = MessageReply().simple_push(query, receiver=receiver)

    if not result:
        logger.warn("机器人探测推送失败，请检查机器人是否正常")
        return 0

    # eg: {"code": 200, "message": "指令已加入代发队列中！", "data": "1806166646799163392"}
    result["msg_id"] = result.get("data") or ""
    RebotDetection.create(opt_type=RebotType.DETECT_SEND, text=short_sentence, **result)


def autodetect_rebot_reply() -> int:
    default_timeout = 60

    # 找到最近的推送消息
    sent_obj = RebotDetection.get_latest_from_already_sent()

    if sent_obj is None:
        return 1

    if sent_obj.code == 200:
        if sent_obj.reply_times < 3:
            RebotDetection.update_reply_times_by_id(sent_pk=sent_obj.id)
            return 1

    return 2

