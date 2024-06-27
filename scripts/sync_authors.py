import json
import re
import os.path
import itertools
from operator import itemgetter, attrgetter
from datetime import timedelta, datetime, date
from urllib.parse import urlparse, parse_qs

from sqlalchemy.orm import load_only

from wecom.utils.log import logger
from wecom.apps.worktool.models.top_author import TopAuthor
from wecom.apps.worktool.models.author_delivery import AuthorDelivery


class SyncAuthorRules:
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

    def trigger_ai_workflow(self):
        pass

    def sync_records(self):
        logger.info('SyncAuthorRules.sync_records => 【开始】同步數據')

        today = date.today()
        now = datetime(year=today.year, month=today.month, day=today.day)
        queryset = TopAuthor.query.filter(TopAuthor.create_time >= now).all()

        for record in queryset:
            if len(record.word_count.strip()) == "0":
                pass

        logger.info('SyncAuthorRules.sync_records => 【結束】同步數據')


if __name__ == "__main__":
    from runserver import app

    with app.app_context():
        pass
