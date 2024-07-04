from urllib.parse import urlparse, parse_qs
from datetime import date, datetime, timedelta

import chinese_calendar as calendar
from wecom.utils.log import logger


class RulesBase:
    @staticmethod
    def parse_url_params(url):
        parsed_url = urlparse(url)  # 解析 URL
        fragment = parsed_url.fragment  # 获取 URL 的 fragment 部分
        fragment_params = urlparse(f"//{fragment}")  # 解析 fragment 中的参数
        query_params = parse_qs(fragment_params.query)  # 获取查询参数

        return query_params

    def _get_platform(self, scr_url):
        exclude_list = ["www", "com", "cn", "net"]
        domain_keywords = {
            "番茄": "fanqie",
            "起点": "qidian",
            "豆瓣": "douban",
            "晋江": "jjwxc",
        }

        ret = urlparse(scr_url)
        hostname = ret.hostname or ""
        domain_list = [s for s in hostname.split(".") if s and s not in exclude_list]

        for platform, keyword in domain_keywords.items():
            if any(keyword in d for d in domain_list):
                return platform

        return ""

    def is_workday(self, dt: datetime = None):
        """ 是否为工作日 """
        dt = date.today() if dt is None else dt
        dt_str = dt.strftime("%Y-%m-%d")
        is_work = calendar.is_workday(dt)

        if is_work:
            logger.info("日期: %s 是工作日", dt_str)
        else:
            logger.info("日期: %s 是法定调休日", dt_str)

        return is_work

    def get_previous_workday(self, dt: datetime) -> date:
        """ 获取上一个工作日 """
        cur_dt = dt - timedelta(days=1)
        if calendar.is_workday(cur_dt):
            return cur_dt.date()

        return self.get_previous_workday(cur_dt)

