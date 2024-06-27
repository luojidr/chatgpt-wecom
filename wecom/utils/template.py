import os
import re
from datetime import date
from typing import List


class TemplateBase:
    _title = None
    template = None

    order_mapping = {
        1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤",
        6: "⑥", 7: "⑦", 8: "⑧", 9: "⑧", 10: "⑩"
    }

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

    @property
    def title(self):
        push_date = date.today().strftime("%m-%d")
        return self._title.format(push_date=push_date)

    def get_text(self, fmt_text, fmt_kwargs, order_index):
        pattern = re.compile(r'：\{(.*?)\}')
        match = pattern.search(fmt_text)

        if match:
            target_name = match.group(1)
            if fmt_kwargs.get(target_name):
                fmt_kwargs["order"] = self.order_mapping[order_index]
                return fmt_text.format(**fmt_kwargs)


class TopAuthorNewWorkTemplate:
    """ 头部作者新作推荐 """
    def __init__(self,
                 author: str, works_name: str, theme: str, core_highlight: str, core_idea: str,
                 pit_date: str, ai_score: str, detail_url: str, src_url: str, platform: str
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
        :param platform: 出处平台
        """
        self.author = author
        self.works_name = works_name
        self.theme = theme
        self.core_highlight = core_highlight
        self.core_idea = core_idea
        self.pit_date = pit_date
        self.ai_score = ai_score
        self.detail_url = detail_url
        self.src_url = src_url
        self.platform = platform


class TopAuthorNewWorkContent(TemplateBase):
    _title = "[{push_date}] 今日高分IP推荐\n"
    template = """
        {number}、{author}《{works_name}》
        {order}题材类型：{theme}
        {order}核心亮点：{core_highlight}
        {order}核心创意：{core_idea}
        {order}开坑时间：{pit_date}
        {order}AI评分：{ai_score}
          评分链接：{detail_url}
        {order}出处链接：{src_url}
        {order}平台：{platform}
    """

    def __init__(self, templates: List[TopAuthorNewWorkTemplate]):
        self.templates = templates

    def get_layout_content(self):
        content_list = []
        pattern = re.compile(r'：\{(.*?)\}')
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

        return self.title + "\n".join(content_list).strip()


class AuthorTemplate:
    """ 作者新番(每天新增的作品) """

    def __init__(self, author: str, works_name: str, theme: str, brief: str, src_url: str, platform: str):
        """
        :param author: 作者名
        :param works_name: 作品名
        :param theme: 题材类型
        :param brief: 作者/作品简介
        :param platform: 出处平台
        :param src_url: 原文链接
        """
        self.author = author
        self.works_name = works_name
        self.theme = theme
        self.brief = brief
        self.src_url = src_url
        self.platform = platform


class AuthorContentCouple(TemplateBase):
        _title = "[{push_date}] 头部作者开新坑啦\n"
        template = """
            {number}、{author}
            {order}新坑名称：{works_name}
            {order}题材类型：{theme}
            {order}新坑链接：{platform} {src_url}
            {order}作者简介：{brief}
        """

        def __init__(self, templates: List[AuthorTemplate]):
            self.templates = templates

        def get_layout_content(self):
            content_list = []
            template_items = self.get_aligned_template_items()

            for number, template in enumerate(self.templates, 1):
                order_index = 0
                kwargs = dict(number=number, **template.__dict__)
                text_list = []

                for line_str in template_items:
                    order_index += 1
                    text = self.get_text(line_str, kwargs, order_index)
                    if text:
                        text_list.append(text)
                    else:
                        order_index -= 1

                content_list.append("\n".join(text_list) + "\n")

            return self.title + "\n".join(content_list).strip()


class AuthorContentMore(TemplateBase):
    _title = "[{push_date}] 头部作者开新坑啦\n"
    template = """
            今天共有{author_cnt}位作者开新坑
    
            1、{author}
            ①新坑名称：{works_name}
            ②题材类型：{theme}
            ③新坑链接：{platform} {src_url}
            ④作者简介：{brief}
            
            2、其他头部作者
             ①作者姓名：{authors}
             ②新坑详情：{detail_url}
        """

    def __init__(self, templates: List[AuthorTemplate]):
        self.templates = templates

    def get_layout_content(self):
        kwargs = dict(
            authors="、".join([template.author for template in self.templates[1:]]),
            detail_url=os.environ["MY_HOST"] + "/top/author/more",
            **self.templates[0].__dict__
        )

        template_items = self.get_aligned_template_items()
        new_template = "\n".join(template_items)

        return self.title + new_template.format(**kwargs)

