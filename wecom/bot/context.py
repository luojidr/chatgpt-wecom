import enum


class ContextType(enum.Enum):
    TEXT = 1            # 文本
    IMAGE_CREATE = 2    # 创建图片


class WTTextType(enum.Enum):
    UNKNOWN = 0             # 未知
    TEXT = 1                # 文本
    IMAGE = 2               # 图片
    VOICE = 3               # 语音
    VIDEO = 5               # 视频
    MINI_PROGRAM = 7        # 小程序
    LINK = 8                # 链接
    FILE = 9                # 文件
    MERGE_RECORD = 13       # 合并记录
    TEXT_WITH_REPLY = 15    # 带回复文本


class Context:
    def __init__(self, type: ContextType = None, content=None, kwargs=None):
        self.type = type
        self.content = content
        self.kwargs = kwargs or {}

    def __contains__(self, key):
        if key == "type":
            return self.type is not None
        elif key == "content":
            return self.content is not None
        else:
            return key in self.kwargs

    def __getitem__(self, key):
        if key == "type":
            return self.type
        elif key == "content":
            return self.content
        else:
            return self.kwargs[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        if key == "type":
            self.type = value
        elif key == "content":
            self.content = value
        else:
            self.kwargs[key] = value

    def __delitem__(self, key):
        if key == "type":
            self.type = None
        elif key == "content":
            self.content = None
        else:
            del self.kwargs[key]

    def __str__(self):
        return "Context(type={}, content={}, kwargs={})".format(self.type, self.content, self.kwargs)


class ReplyType(enum.Enum):
    TEXT = 1  # 文本
    VOICE = 3  # 音频文件
    IMAGE = 2  # 图片文件
    IMAGE_URL = 4  # 图片URL
    VIDEO_URL = 5  # 视频URL
    FILE = 6  # 文件
    CARD = 7  # 微信名片，仅支持ntchat
    INVITE_ROOM = 8  # 邀请好友进群
    INFO = 9
    ERROR = 10
    TEXT_ = 11  # 强制文本
    VIDEO = 12
    MINIAPP = 13  # 小程序

    def __str__(self):
        return self.name


class Reply:
    def __init__(self, type: ReplyType = None, content=None):
        self.type = type
        self.content = content

    def __str__(self):
        return "Reply(type={}, content={})".format(self.type, self.content)
