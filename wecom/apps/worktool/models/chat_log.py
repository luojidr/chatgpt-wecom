import re
import time
import string
import random
import os.path
import traceback
from collections import namedtuple
from typing import Optional, Dict, Any

from sqlalchemy import Column, Integer, String, Float, Enum

from wecom.core.database import db, Column, BaseModel

# from database.models.chat_prompt import ChatPrompt
# from database.models.openai_call_log import OpenaiCallLog
# from common.log import logger
# from common.compute_tokens import get_tokens_cost, get_text_cost, get_image_cost
# from channel.chat_message import ChatMessage

FILE_TYPE = "file"
Message = namedtuple("Message", ["agent", "source", "id", "time", "type", "content"])


class ChatLog(BaseModel):
    __tablename__ = 'chat_log'

    user_id = Column(Integer, nullable=False, server_default='0')
    openai_call_id = Column(Integer, nullable=False, server_default='0')
    username = Column(String(200), nullable=False, server_default='')
    msg_id = Column(String(200), nullable=False, server_default='')
    msg_type = Column(String(200), nullable=False, server_default='')
    msg_time = Column(Integer, nullable=False, server_default='0')
    file_path = Column(String(200), nullable=False, server_default="")  # 文件路径
    file_ext = Column(String(20), nullable=False, server_default="")   # 文件格式
    media_id = Column(String(200), nullable=False, server_default="")   # 图片、语音的 media_id
    cost = Column(Float, nullable=False, server_default="0.0")      # tokens 花费

    @classmethod
    def create(cls, message: Optional[messages.BaseMessage] = None, **kwargs) -> int:
        """ 记录聊天和openai历史 """
        from channel.wechatcom.wechatcomapp_channel import WechatComAppChannel

        tokens, cost = 0, 0.0
        model_type = conf().get("model")

        # 文本、语音、图片、视频等时：包含 message 对象， kwargs 为空
        # 上传文件时： kwargs 包含: file_path, userid, content； message 为空
        file_ext = ""
        file_path = kwargs.get("file_path")

        try:
            if file_path:
                # 上传文件
                userid = kwargs.get("userid")
                user = session.query(User).filter_by(userid=userid).first()
                username = user.userid if user else WechatComAppChannel().client.user.get(userid)["userid"]

                # 构造一个message对象
                message = Message(
                    agent=conf().get("wechatcomapp_agent_id", 0), type=FILE_TYPE,
                    source=username, content=kwargs.get("content", ""), time=int(time.time()),
                    id="".join(random.choices(string.digits + string.ascii_letters, k=19)),
                )
                _, file_ext = os.path.splitext(file_path)
            else:
                logger.info("create chat log message.source: [%s]", message.source)
                user = session.query(User).filter(User.userid == message.source).first()

            values = dict(
                user_id=user.id,
                username=message.source if message else "",
                msg_id=message.id if message else "",
                msg_time=message.time if message else "",
                msg_type=message.type.upper() if message else "",
                file_ext=file_ext, file_path=file_path or ""
            )

            if message:
                if message.type not in [messages.TextMessage.type, FILE_TYPE]:
                    values["media_id"] = message.media_id
                else:
                    tokens_cost_dict = get_tokens_cost(message.content, model_type=model_type)
                    tokens, cost = tokens_cost_dict.values()
                    values["cost"] = cost

            instance = cls(**values)
            session.add(instance)
            session.commit()
        except Exception as e:
            instance = None
            logger.error("ChatLog create err: %s", e)
            logger.error(traceback.format_exc())
        else:
            # 记录输入的openai历史
            try:
                openai_call_obj = OpenaiCallLog(
                    user_id=user.id, input_str=message.content,
                    input_tokens=tokens, model_type=model_type
                )
                session.add(openai_call_obj)
                session.commit()

                if instance:
                    session.query(cls).filter_by(id=instance.id).update({"openai_call_id": openai_call_obj.id})
                    session.commit()
            except Exception as err:
                logger.error("OpenaiCallLog create err: %s", err)
                logger.error(traceback.format_exc())

        return instance and instance.id

    @classmethod
    def update_chat_response_log(cls,
                                 chat_log_id: int,
                                 output_str: Optional[str] = None,
                                 output_tokens: Optional[int] = None,
                                 prompt_tokens: Optional[int] = None,
                                 completion_tokens: Optional[int] = None,
                                 total_tokens: Optional[int] = None,
                                 is_group: bool = False,
                                 ):
        """ 更新调用openai大模型后的使用成本(文本类) """
        if not output_str and not output_tokens:
            return

        try:
            token_type = "output"
            model_type = conf().get("model")
            instance = session.query(cls).filter(cls.id == chat_log_id).first()

            if not instance:
                logger.warning("OpenaiCallLog update_chat_response_log -> chat_log_id: %s not exist", chat_log_id)
                return

            chat_total_tokens = 0
            openai_call_id = instance.openai_call_id
            openai_call_obj = session.query(OpenaiCallLog).filter_by(id=openai_call_id).first()

            tokens_cost_dict = get_tokens_cost(output_str, output_tokens, token_type=token_type, model_type=model_type)
            tokens, cost = tokens_cost_dict.values()

            if openai_call_obj:
                chat_total_tokens = total_tokens if total_tokens else (instance.input_tokens + tokens)

                openai_call_obj.output_str = output_str
                openai_call_obj.output_tokens = tokens
                openai_call_obj.prompt_tokens = prompt_tokens
                openai_call_obj.completion_tokens = completion_tokens
                openai_call_obj.total_tokens = total_tokens

                session.add(openai_call_obj)
                session.commit()

            instance.cost = get_text_cost(chat_total_tokens, token_type=token_type,  model_type=model_type)
            session.add(instance)
            session.commit()

            cls.save_potential_prompts(
                user_id=instance.user_id,
                chat_log_id=instance.id,
                output_str=output_str,
                is_group=is_group
            )
            return instance
        except Exception as e:
            logger.error("OpenaiCallLog update_chat_response_log -> err: %s", e)
            logger.error(traceback.format_exc())

    @classmethod
    def update_chat_image_log(cls, chat_log_id: int, img_url: str, revised_prompt: str = ""):
        """ 更新生成图片的成本 """
        model_type = conf().get("text_to_image")

        try:
            instance = session.query(cls).filter(cls.id == chat_log_id).first()
            if not instance:
                return

            openai_call_id = instance.openai_call_id
            openai_call_obj = session.query(OpenaiCallLog).filter_by(id=openai_call_id).first()

            if openai_call_obj:
                openai_call_obj.output_str = img_url
                openai_call_obj.revised_prompt = revised_prompt

                session.add(openai_call_obj)
                session.commit()

            instance.msg_type = "IMAGE"
            instance.cost = get_image_cost(model_type=model_type)

            session.add(instance)
            session.commit()

            return instance
        except Exception as e:
            logger.error("OpenaiCallLog update_chat_image_log -> err: %s", e)
            logger.error(traceback.format_exc())

    @classmethod
    def save_potential_prompts(cls,  user_id: int, chat_log_id: int, output_str: str, is_group: bool = False):
        """ 解析并保存可能提示词 """
        regex = re.compile(r".*?={25,50}.*?1\)(.*?)2\)(.*?)3\)(.*?)$", re.M | re.S)
        m = regex.search(output_str)

        if m is None:
            logger.error("请注意：没有找到相关的【提示词】")
            return []

        results = regex.search(output_str).groups()
        cleaned_prompts = [s.strip() for s in results]
        ChatPrompt.create(user_id=user_id, chat_log_id=chat_log_id, prompts=cleaned_prompts, is_group=is_group)

    @classmethod
    def create_by_wx(cls, cmsg: ChatMessage, session_id: str = None):
        """ 记录微信聊天和openai历史 """
        tokens, cost = 0, 0.0
        model_type = conf().get("model")

        # 文本、语音、图片、视频等时：包含 message 对象， kwargs 为空
        # 上传文件时： kwargs 包含: file_path, userid, content； message 为空
        # file_ext = ""
        # file_path = kwargs.get("file_path")
        file_path = ""
        session_id = session_id or cmsg.other_user_id
        logger.info("[ChatLog.create_by_wx] create chat log cmsg.username: [%s]", session_id)

        try:
            wx_user = WXUser.get_user_by_username(username=session_id)
            logger.info("create_by_wx => wx_user: %s", wx_user)

            if wx_user is None:
                return

            if file_path:
                # 上传文件
                # userid = kwargs.get("userid")
                # user = session.query(User).filter_by(userid=userid).first()
                # username = user.userid if user else WechatComAppChannel().client.user.get(userid)["userid"]
                #
                # 构造一个message对象
                # message = Message(
                #     agent=conf().get("wechatcomapp_agent_id", 0), type=FILE_TYPE,
                #     source=username, content=kwargs.get("content", ""), time=int(time.time()),
                #     id="".join(random.choices(string.digits + string.ascii_letters, k=19)),
                # )
                # _, file_ext = os.path.splitext(file_path)
                pass

            values = dict(
                user_id=wx_user.user_id,
                username=wx_user.nickname,
                msg_id=cmsg.msg_id,
                msg_time=cmsg.create_time,
                msg_type=cmsg.ctype,
                file_ext=""
            )

            # if cmsg.ctype not in [messages.TextMessage.type, FILE_TYPE]:
            #     values["media_id"] = message.media_id
            # else:
            #     pass

            tokens_cost_dict = get_tokens_cost(cmsg.content, model_type=model_type)
            tokens, cost = tokens_cost_dict.values()
            values["cost"] = cost

            instance = cls(**values)
            session.add(instance)
            session.commit()
        except Exception as e:
            instance = None
            logger.error("[ChatLog.create_by_wx] ChatLog create err: %s", e)
            logger.error(traceback.format_exc())
        else:
            # 记录输入的openai历史
            try:
                openai_call_obj = OpenaiCallLog(
                    user_id=wx_user.user_id, input_str=cmsg.content,
                    input_tokens=tokens, model_type=model_type
                )
                session.add(openai_call_obj)
                session.commit()

                if instance:
                    session.query(cls).filter_by(id=instance.id).update({"openai_call_id": openai_call_obj.id})
                    session.commit()
            except Exception as err:
                logger.error("[ChatLog.create_by_wx] OpenaiCallLog create err: %s", err)
                logger.error(traceback.format_exc())

        return instance and instance.id


