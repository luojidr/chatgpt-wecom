import re
from datetime import date
from typing import List


class TemplateBase:
    template = None

    def get_aligned_template_items(self):
        assert self.template, "模版不能为空"

        space_cnt = 0
        results = []
        parts = self.template.split("\n")[1:]

        for c in parts[0]:
            if c.isspace():
                space_cnt += 1
            else:
                break

        for line in parts:
            if not line[:space_cnt].strip():
                results.append(line[space_cnt:])
            else:
                results.append(line)

        return results


class TopAuthorNewWorkTemplate:
    """ 头部作者新作推荐 """
    def __init__(self,
                 author: str, works_name: str, theme: str, core_highlight: str,
                 core_idea: str, pit_date: str, ai_score: str, detail_url: str, src_url: str
                 ):
        """
        :param author: 作者名
        :param works_name: 作品名
        :param theme: 题材类型
        :param core_highlight: 核心亮点
        :param core_idea: 核心创意
        :param pit_date: 开坑时间 0000-00-00
        :param ai_score: AI评分
        :param detail_url: 评估详情见链接
        :param src_url: 原文链接
        """
        self.author = author
        self.works_name = works_name
        self.theme = theme
        self.author = author
        self.core_highlight = core_highlight
        self.core_idea = core_idea
        self.pit_date = pit_date
        self.ai_score = ai_score
        self.detail_url = detail_url
        self.src_url = src_url


class TopAuthorNewWorkContent(TemplateBase):
    title = "[{push_date}] 今日高分IP推荐\n"
    template = """
        {number}、{author}《{works_name}》
        {order}题材类型：{theme}
        {order}核心亮点：{core_highlight}
        {order}核心亮点：{core_idea}
        {order}开坑时间：{pit_date}
        {order}AI评分：{ai_score}
          评分链接：{detail_url}
        {order}出处链接：{src_url}
    """

    def __init__(self, templates: List[TopAuthorNewWorkTemplate]):
        self.templates = templates
        self.order_mapping = {
            1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤",
            6: "⑥", 7: "⑦", 8: "⑧", 9: "⑧", 10: "⑩"
        }

    def get_layout_content(self):
        content_list = []
        pattern = re.compile(r'：\{(.*?)\}')
        push_date = date.today().strftime("%m-%d")
        template_items = self.get_aligned_template_items()

        for number, template in enumerate(self.templates, 1):
            order_index = 0
            kwargs = dict(number=number, **template.__dict__)
            text_list = [template_items[0].format(**kwargs)]

            for line_str in template_items[1:]:
                match = pattern.search(line_str)

                if match:
                    target_name = match.group(1)
                    if kwargs.get(target_name):
                        order_index += 1
                        kwargs["order"] = self.order_mapping[order_index]
                        text_list.append(line_str.format(**kwargs))

            content_list.append("\n".join(text_list) + "\n")

        return self.title.format(push_date=push_date) + "\n".join(content_list).strip()

