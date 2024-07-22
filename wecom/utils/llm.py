import uuid
from multiprocessing.dummy import Pool as ThreadPool

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt

from config import prompts
from wecom.utils.log import logger
from wecom.apps.worktool.service.chat import ChatCompletion

__all__ = ["AuthorRetrievalByBingSearch"]


class AuthorRetrievalByBingSearch:
    def __init__(self, author: str, platform: str):
        self._author = author
        self._platform = platform

        self._api_path = "https://api.bing.microsoft.com/v7.0/search"
        self._subscription_key = "46d0f028eba7499fbff9bca7b3137d6d"

    def is_chinese_proportion_above_80(self, text):
        total_length = len(text)
        chinese_length = 0
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff':
                chinese_length += 1
        return chinese_length / total_length > 0.5

    @retry(stop=stop_after_attempt(max_attempt_number=3))
    def get_content(self, url, text_num=2000):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        texts = list(soup.stripped_strings)
        res = ','.join([t for t in texts[7:] if self.is_chinese_proportion_above_80(t)])[:text_num]
        return res

    @retry(stop=stop_after_attempt(max_attempt_number=3))
    def get_bing_results(self, query: str, subscription_key: str = None, timeout: int = 5):
        params = {"q": query, "textDecorations": True, "textFormat": "HTML", 'count': 1, "mkt": "zh-CN"}
        response = requests.get(
            self._api_path,
            headers={
                "Ocp-Apim-Subscription-Key": subscription_key or self._subscription_key
            },
            params=params,
            timeout=timeout,
        )

        if not response.ok:
            logger.error(f"BingSearch Error: {response.status_code} {response.text}")
            raise ValueError("BingSearch Error: %s" % response.text)

        return response.json()

    def search_by_bing(self, query: str, subscription_key: str = None, retry_times: int = 2):
        contents = []
        snippets = []
        bing_results = []

        pool = ThreadPool()

        for i in range(retry_times):
            res = self.get_bing_results(query=query, subscription_key=subscription_key)
            bing_results.append(res)

            value_list = res['webPages']["value"]
            snippets.extend([page['snippet'] for page in value_list])
            results = pool.map(self.get_content, [page['cachedPageUrl'] for page in value_list if 'cachedPageUrl' in page])
            contents.extend(results)

        pool.close()
        pool.join()

        return dict(
            bing_results=bing_results,
            text=';'.join(snippets) + ';'.join(contents),
        )

    def get_invoked_result_by_llm(self):
        fmt_kwargs = {
            "author": self._author,
            "platform": self._platform
        }
        query = f'百度百科: 作者:{self._author}'

        result_dict = self.search_by_bing(query=query)
        fmt_kwargs.update({"prompt": result_dict["text"]})
        messages = [dict(role="system", content=prompts.TOP_AUTHOR_PROMPT.format(**fmt_kwargs))]

        session_id = str(uuid.uuid1()).replace("-", "")  # 随机 session_id
        response = ChatCompletion(session_id).get_completions(messages=messages)

        return dict(
            session_id=session_id,
            bing_results=result_dict["bing_results"],
            content=response.choices[0].message.content
        )


if __name__ == '__main__':
    import re
    import pandas as pd
    authors = [
        "白羽摘雕弓",
        "藤萝为枝",
    ]
    platform = "晋江"
    data = {'作者': [], '介绍': []}
    results = []
    for author in authors:
        result = AuthorRetrievalByBingSearch(author, platform).get_invoked_result_by_llm()
        llm_content = result["content"]
        brief_pattern = re.compile(r"4、.*?一句话提炼.*?市场表现等的具体亮点.*?：(.*)$", re.M | re.S)
        brief_match = brief_pattern.search(llm_content)
        if brief_match:
            brief = brief_match.group(1).strip().lstrip(' -')
            brief = brief.split("\n", 1)[0].strip()
            print(brief)
            results.append({'作者': author, '介绍': brief})
    df = pd.DataFrame(results)
    df.to_excel("authors_info.xlsx", index=False)