import os
import re
from datetime import date
from typing import List, Optional

from wecom.apps.external_groups.models.script_delivery import ScriptDelivery


class TemplateBase:
    _title = None
    template = None

    order_mapping = {
        1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤",
        6: "⑥", 7: "⑦", 8: "⑧", 9: "⑧", 10: "⑩"
    }

    def get_aligned_template_items(self, template: str = None):
        template = template or self.template
        assert template, "模版不能为空"

        space_cnt = 0
        results = []
        parts = template.split("\n")[1:]

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
        push_date = date.today().strftime("%H:%M:%S")
        return self._title.format(push_date=push_date)

    def get_text(self, fmt_text, fmt_kwargs):
        pattern = re.compile(r'\{(.*?)\}')
        match = pattern.search(fmt_text)

        if match:
            target_name = match.group(1)
            if fmt_kwargs.get(target_name):
                # order_index = fmt_kwargs["order_index"]
                # fmt_kwargs["order"] = self.order_mapping[order_index]
                return fmt_text.format(**fmt_kwargs)


class NewWorkTemplate:
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


class NewWorkContent(TemplateBase):
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
    tips = "\n\n近半个月所有题材中【评分≥8.5】的新IP合集，也在持续更新中。如需获取最新合集，请@我，并回复“8.5”"

    def __init__(self, templates: List[NewWorkTemplate]):
        self.templates = templates

    @staticmethod
    def has_tips_with_gte_score():
        queryset = ScriptDelivery.query_by_ai_score(operator="gte", limit=None)
        return len(queryset) > 0

    def get_layout_content(self):
        content_list = []
        pattern = re.compile(r'\{(.*?)\}')
        template_items = self.get_aligned_template_items()

        for number, template in enumerate(self.templates, 1):
            order_index = 0
            kwargs = dict(number=number, **template.__dict__)
            text_list = [template_items[0].format(**kwargs)]

            for line_str in template_items[1:]:
                match_list = pattern.findall(line_str)

                if match_list:
                    # 序列+后面的字段非空的
                    if "order" in match_list and kwargs.get(match_list[-1]):
                        order_index += 1
                        kwargs["order"] = self.order_mapping[order_index]

                    text_list.append(line_str.format(**kwargs))

            content_list.append("\n".join(text_list) + "\n")

        content = self.title + "\n".join(content_list).strip()

        if self.has_tips_with_gte_score():
            content = content + self.tips

        return content


class NewWorkContentMore(TemplateBase):
    _title = ""
    template = """
            共有{work_cnt}个{target_score}分IP推荐

            1、{author}《{works_name}》
            ①题材类型：{theme}
            ②核心亮点：{core_highlight}
            ③核心创意：{core_idea}
            ④开坑时间：{pit_date}
            ⑤AI评分：{ai_score}
              评分链接：{detail_url}
            ⑥出处链接：{src_url}
            ⑦平台：{platform}
        """
    another_template = """
           2、{author}《{works_name}》
            ①题材类型：{theme}
            ②核心亮点：{core_highlight}
            ③核心创意：{core_idea}
            ④开坑时间：{pit_date}
            ⑤AI评分：{ai_score}
              评分链接：{detail_url}
            ⑥出处链接：{src_url}
            ⑦平台：{platform}
        """

    tips_template = """
            2、其他{target_score}分IP
            ①IP名：{work_names}
            ②IP详情：{more_detail_url}
    """

    def __init__(self, templates: List[NewWorkTemplate], batch_id: str, target_score: float):
        self.templates = templates
        self.batch_id = batch_id
        self.target_score = target_score

    def get_layout_content(self):
        content = ""
        work_cnt = len(self.templates)
        two_template_map = {1: self.template, 2: self.another_template}

        if len(self.templates) <= 2:
            for index, _template in enumerate(self.templates, 1):
                template_items = self.get_aligned_template_items(template=two_template_map[index])
                template_fmt = "\n".join(template_items)
                fmt_kwargs = dict(work_cnt=work_cnt,  target_score=self.target_score, **_template.__dict__)
                content += template_fmt.format(**fmt_kwargs) + "\n"
        else:
            fmt_kwargs = dict(work_cnt=work_cnt, target_score=self.target_score, **self.templates[0].__dict__)
            template_items = self.get_aligned_template_items()
            template_fmt = "\n".join(template_items)
            content = template_fmt.format(**fmt_kwargs) + "\n"

            tips_kwargs = dict(
                target_score=self.target_score,
                work_names="、".join([template.works_name for template in self.templates[1:]]),
                more_detail_url=os.environ["MY_HOST"] + "/wecom/new_work/more?bid=%s" % self.batch_id,
            )
            tips_template_items = self.get_aligned_template_items(template=self.tips_template)
            tips_template_fmt = "\n".join(tips_template_items)
            content += tips_template_fmt.format(**tips_kwargs)

        return content.strip()


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
            ①新坑名称：{works_name}
            ②题材类型：{theme}
            ③新坑链接：{platform} {src_url}
            ④作者简介：{brief}
        """

        def __init__(self, templates: List[AuthorTemplate]):
            self.templates = templates

        def get_layout_content(self):
            content_list = []
            template_items = self.get_aligned_template_items()

            for number, template in enumerate(self.templates, 1):
                kwargs = dict(number=number, **template.__dict__)
                text_list = []

                for line_str in template_items:
                    text = self.get_text(line_str, kwargs)
                    if text:
                        text_list.append(text)

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

    def __init__(self, templates: List[AuthorTemplate], batch_id: str):
        self.templates = templates
        self.batch_id = batch_id

    def get_layout_content(self):
        main_author = self.templates[0]
        other_authors = self.templates[1:]

        main_kwargs = dict(
            author=main_author.author,
            works_name=main_author.works_name,
            theme=main_author.theme,
            platform=main_author.platform,
            src_url=main_author.src_url,
            brief=main_author.brief
        )

        other_authors_info = []
        for author in other_authors:
            other_authors_info.append({
                "author": author.author,
                "works_name": author.works_name,
                "theme": author.theme,
                "platform": author.platform,
                "src_url": author.src_url,
                "brief": author.brief
            })

        kwargs = dict(
            author_cnt=len(self.templates),
            authors="、".join([template.author for template in other_authors]),
            detail_url=os.environ["MY_HOST"] + "/wecom/top_author/more?bid=%s" % self.batch_id,
            **main_kwargs
        )

        template_items = self.get_aligned_template_items()
        new_template = "\n".join(template_items)

        content = self.title + new_template.format(**kwargs)
        return content

