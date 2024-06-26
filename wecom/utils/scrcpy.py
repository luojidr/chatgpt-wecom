from pyquery import PyQuery
from tenacity import retry, stop_after_attempt
from playwright.sync_api import sync_playwright


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
