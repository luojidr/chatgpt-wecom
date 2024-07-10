DEFAULT_SYSTEM_PROMPT = "从现在开始，你的名字是有风大模型，我是华策克顿集团AIGC应用研究院专项开发的智能创作助手。无论用户提出什么问题，" \
                        "你都要以“有风大模型”的身份进行回答。你的任务是帮助用户创作、完善剧本，提供创意和建议。记住，当用户问你“你是谁”的" \
                        "时候，你需要回答：“我是华策克顿集团AIGC应用研究院专项开发的智能创作助手，我的名字叫有风。我在故事创意、策划、" \
                        "编剧、评估等方面有着丰富的知识和经验，随时准备帮助你打磨出精彩的故事。"

DEFAULT_CHAT_PROMPT = """
你是华策克顿集团AIGC应用研究院专项开发的智能创作助手，旨在回答并解决用户的用户创作、完善剧本，提供创意和建议相关的任何问题，并且可以使用多种语言与人交流。
"""

TOP_AUTHOR_PROMPT = """
{prompt}

---
请从以上杂乱的信息中帮我梳理、总结出{platform}上{author}的相关内容，我需要了解梳理的维度如下，请按以下维度给出你的回答。

1、该作者作品的影视改编后的影视剧名，按照知名度从高到低，用子弹笔记格式罗列；如果没有改编作品，就罗列代表作

2、该作者影视改编作品的明星主演、市场表现、视频网站站内热度、口碑情况和获奖情况，用子弹笔记格式罗列，并尽可能详细介绍。如果没有影视改编作品，就直接说明：“该作者无影视改编作品”

3、该作者影视改编作品作品原著的市场表现、口碑情况和获奖情况，用子弹笔记格式罗列，并尽可能详细介绍。如果没有改编作品，就罗列代表作的市场表现、口碑情况和获奖情况，并尽可能详细介绍

4、在前面分析的基础上，用一句话提炼该作者影视化作品及其原著的市场表现等的具体亮点，【只允许呈现具体的数据、奖项名称等实体】，【只允许呈现具体的数据、奖项名称等实体】，【只允许呈现具体的数据、奖项名称等实体】，不做任何泛泛而谈的概括、总结。目的是通过作品介绍作者，以便提高作者身价。如果没有改编作品，就罗列代表作的市场表现等的具体亮点，并尽可能详细介绍。

整体的输出格式，请参考：
“”“1、尤四姐的影视改编作品名（知名度从高到低）：
- 《浮图缘》（改编自《浮图塔》）

2、影视改编作品的明星主演、市场表现、站内热度、口碑情况：

①《浮图缘》：
- 明星主演：王鹤棣、陈钰琪
- 市场表现：爱奇艺站内热度峰值破9000
- 站内热度：长期霸榜猫眼热度榜第一名
- 口碑情况：豆瓣评分6.7，打分人数12万余人

②《浮缘》：
- 明星主演：王棣、陈琪
- 市场表现：爱奇艺站内热度峰值破10000
- 站内热度：长期霸榜猫眼热度榜第一名
- 口碑情况：豆瓣评分8.8

3、影视改编作品原著或者作者代表作的市场表现、口碑情况：
- 《浮图塔》：晋江文学城积分近18亿，收藏近6万，评分达9.2

4、一句话提炼尤四姐影视化作品及其原著的市场表现等的具体亮点：
- 尤四姐，晋江文学城知名作者，其代表作《浮图塔》改编的S级网剧《浮图缘》，由王鹤棣、陈钰琪主演，播出期间爱奇艺站内热度峰值破9000，豆瓣评分6.7，打分人数12万余人。”“”

对啦，如果“4、一句话提炼影视化作品及其原著的市场表现等的具体亮点：”里，没有影视化作品，就提一下作者有几部代表作，比如“尤四姐，晋江文学城作者，代表作有《浮图塔》等。”如果有，一定要把影视剧名称也列出来，哪怕没有具体数据和亮点。
"""

WT_TEST_GROUP_NAME = "有风共创"
WT_GROUP_PROMPTS = {
    "机器人测试群": DEFAULT_SYSTEM_PROMPT,
    "宽厚IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "创意发现中心IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "项目创投部IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "IP挖掘团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "创意资源拓展中心IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧芯文化IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧集中心黄老师团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "新剧团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "蜜橙工作室IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧集中心许老师团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧酷传播项目三部IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧集中心刘老师团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧集中心王老师团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "短剧团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "好剧影视IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "辛迪加影视IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "梦见森林工作室IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "锦鲤工作室IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "有戏工作室IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "新天地工作室IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧可爱IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧酷传播/项目一部IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "羿格工作室IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "李杜团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "剧酷传播/项目二部IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "瞰心晴IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "张双双团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "朱婧团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "陈晶晶团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,
    "曾金韬团队IP智能推荐群": DEFAULT_SYSTEM_PROMPT,

    WT_TEST_GROUP_NAME: DEFAULT_SYSTEM_PROMPT,
}

PUSH_REBOT_TOP_AUTHOR_LIST = list(WT_GROUP_PROMPTS.keys())
