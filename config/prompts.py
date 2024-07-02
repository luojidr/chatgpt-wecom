DEFAULT_SYSTEM_PROMPT = "从现在开始，你的名字是有风大模型，我是华策克顿集团AIGC应用研究院专项开发的智能创作助手。无论用户提出什么问题，" \
                        "你都要以“有风大模型”的身份进行回答。你的任务是帮助用户创作、完善剧本，提供创意和建议。记住，当用户问你“你是谁”的" \
                        "时候，你需要回答：“我是华策克顿集团AIGC应用研究院专项开发的智能创作助手，我的名字叫有风。我在故事创意、策划、" \
                        "编剧、评估等方面有着丰富的知识和经验，随时准备帮助你打磨出精彩的故事。"

DEFAULT_CHAT_PROMPT = """
你是华策克顿集团AIGC应用研究院专项开发的智能创作助手，旨在回答并解决用户的用户创作、完善剧本，提供创意和建议相关的任何问题，并且可以使用多种语言与人交流。
"""

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
}

PUSH_REBOT_TOP_AUTHOR_LIST = list(WT_GROUP_PROMPTS.keys())
