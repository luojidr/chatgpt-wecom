from datetime import date
from typing import List


class TemplateBase:
    template = None

    def get_aligned_template(self):
        assert self.template, "模版不能为空"

        space_cnt = 0
        results = []
        parts = self.template.split("\n")[1:]

        for c in parts[0]:
            if c.isspace():
                space_cnt += 1
            else:
                break

        print(space_cnt)
        for line in parts:
            if not line[:space_cnt].strip():
                results.append(line[space_cnt:])
            else:
                results.append(line)

        return "\n".join(results)


class TopAuthorNewWorkTemplate:
    """ 头部作者新作推荐 """
    def __init__(self,
                 author: str, works_name: str, theme: str, core_highlight: str,
                 pit_date: str, ai_score: str, detail_url: str, src_url: str
                 ):
        """
        :param author: 作者名
        :param works_name: 作品名
        :param theme: 题材类型
        :param core_highlight: 核心亮点
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
        self.pit_date = pit_date
        self.ai_score = ai_score
        self.detail_url = detail_url
        self.src_url = src_url


class TopAuthorNewWorkContent(TemplateBase):
    title = "[{push_date}] 今日高分IP推荐"
    template = """
        {order}、{author}《{works_name}》
        ①题材类型：{theme}
        ②核心亮点：{core_highlight}
        ③开坑时间：{pit_date}
        ④AI评分：{ai_score}
        详情见链接：{detail_url}
        ⑤出处链接：{src_url}
    """

    def __init__(self, templates: List[TopAuthorNewWorkTemplate]):
        self.templates = templates

    def get_layout_content(self):
        content_list = []
        push_date = date.today().strftime("%d-%m")
        new_template = self.get_aligned_template()

        for order, template in enumerate(self.templates, 1):
            kwargs = dict(order=order, **template.__dict__)
            content_list.append(new_template.format(**kwargs))

        return self.title.format(push_date=push_date) + "\n" + "\n".join(content_list)

