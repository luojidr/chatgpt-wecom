import time
import json
import requests
from collections import deque
from pyquery import PyQuery

from wecom.utils.log import logger

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
})

WEATHER_CONFIG = {
    "上海": "101020100",
}


class Weather:
    CITY_CODE_MAPPING = {}

    def __init__(self, q_city):
        self.q_city = q_city
        logger.info(f"查询天气：{q_city}")

    @property
    def city_code(self):
        if not self.CITY_CODE_MAPPING:
            url = "https://j.i8tq.com/weather2020/search/city.js"
            res = session.get(url, headers={"Host": "j.i8tq.com", "Referer": "https://www.weather.com.cn/"})
            text = res.content.decode("utf-8").replace("var city_data =", "").strip()
            self.CITY_CODE_MAPPING = json.loads(text)

        q = deque([value for city, value in self.CITY_CODE_MAPPING.items()])
        while q:
            node = q.popleft()
            if "AREAID" not in node:
                q.extend([v for k, v in node.items()])
            else:
                if node["NAMECN"] in self.q_city:
                    return node["AREAID"]

        raise ValueError("没有找到对应的城市")

    def get_temperature(self):
        city_code = self.city_code
        url = f"https://d1.weather.com.cn/sk_2d/{city_code}.html?_={int(time.time() * 1000)}"
        res = session.get(url, headers={"Host": "d1.weather.com.cn", "Referer": "https://www.weather.com.cn/"})
        text = res.content.decode("utf-8").replace("var dataSK=", "").strip()
        info = json.loads(text)

        city = info["cityname"]
        date = info["date"]
        temp = info["temp"] + "℃"
        wind = info["WD"] + "：" + info["WS"]
        sd = "相对湿度：" + info["SD"]
        return f"{city} {date}\n温度：{temp}  {wind}  {sd}"

    def get_other_info(self):
        data = []
        city_code = self.city_code
        url = f"https://www.weather.com.cn/weather1d/{city_code}.shtml#search"
        res = session.get(url, headers={"Host": "www.weather.com.cn"})
        text = res.content.decode("utf-8")

        document = PyQuery(text)
        for node in document.items("div.livezs ul li"):
            leval_name = node.find("em").text()
            abbr = node.find("span").text()
            info = node.find("p").text()
            data.append(f"{leval_name}：{abbr}\n  {info}\n")

        return "\n".join(data)

    def get_weather(self):
        try:
            info = self.get_temperature() + "\n\n" + self.get_other_info()
            logger.info(f"查询天气成功: {info}")

            return info
        except Exception as e:
            return str(e)

