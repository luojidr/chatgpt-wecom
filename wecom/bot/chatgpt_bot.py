# encoding:utf-8

import time
import json

import openai
import requests

from .chatgpt_session import ChatGPTSession
from .openai_image import OpenAIImage
from .session_manager import SessionManager
from ..core.token_bucket import TokenBucket
from ..core.log import logger
from .context import ContextType

from config import settings


class ChatGPTBot(OpenAIImage):
    def __init__(self):
        super().__init__()

        openai.api_key = settings.OPENAI_API_KEY
        openai.api_base = settings.OPENAI_API_BASE
        proxy = settings.OPENAI_PROXY

        if proxy:
            openai.proxy = proxy

        self.chatgpt_rate_limit = TokenBucket(settings.CHATGPT_RATE_LIMIT or 20)

        self.model = settings.OPENAI_MODEL or "gpt-3.5-turbo"
        self.sessions = SessionManager(ChatGPTSession, model=self.model)
        self.args = {
            "model": self.model,  # 对话模型的名称
            "temperature": 0.7,  # 值在[0,1]之间，越大表示回复越具有不确定性
            # "max_tokens": 4096,  # 回复最大的字符数
            "top_p": 1,
            "frequency_penalty": 0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
            "presence_penalty": 0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
            "request_timeout": None,  # 请求超时时间，openai接口默认设置为600，对于难问题一般需要较长时间
            "timeout": None,  # 重试超时时间，在这个时间内，将会自动重试
        }

    def create(self, query, context=None):
        logger.warning("ChatGPTBot.create => self: %s context: %s", self, context)
        data = dict(is_ok=True, data={}, type=context.type)

        # acquire reply content
        if context.type == ContextType.TEXT:
            logger.info("[CHATGPT] query={}".format(query if len(query) < 300 else query[:300]))

            session_id = context["session_id"]
            session = self.sessions.session_query(query, session_id)
            logger.debug("[CHATGPT] session query={}".format(session.messages))

            api_key = context.get("openai_api_key")
            model = context.get("gpt_model")
            new_args = None
            if model:
                new_args = self.args.copy()
                new_args["model"] = model

            result = self.get_chat_completions(session, api_key, args=new_args)
            logger.debug(
                "[CHATGPT] new_query={}, session_id={}, content={}, total_tokens={}, completion_tokens={}".format(
                    session.messages, session_id,
                    result["content"], result["total_tokens"], result["completion_tokens"],
                )
            )

            # # 调用 openai 大模型后保存到历史记录中
            # ChatLog.update_chat_response_log(
            #     chat_log_id=context.get("chat_log_id", 0), output_str=reply_content["content"],
            #     prompt_tokens=reply_content.get("prompt_tokens"),
            #     completion_tokens=reply_content.get("completion_tokens"),
            #     total_tokens=reply_content.get("total_tokens"),
            #     is_group=context.kwargs.get("isgroup", False),
            # )

            data["data"] = result
        elif context.type == ContextType.IMAGE_CREATE:
            is_ok, img_url, revised_prompt = self.create_img(query, 0)
            data["is_ok"] = is_ok
            data["data"] = dict(img_url=img_url, revised_prompt=revised_prompt)

            # # 将openai调用的结果记录在历史表中
            # ChatLog.update_chat_image_log(
            #     chat_log_id=context.get("chat_log_id", 0),
            #     img_url=retstring, revised_prompt=revised_prompt
            # )

        else:
            raise ValueError("Not support message type: %s", context.type)

        return data

    def get_chat_completions(self, session: ChatGPTSession, api_key=None, args=None, retry_count=0) -> dict:
        """
        call openai's ChatCompletion to get the answer
        :param session: a conversation session
        :param api_key: api_key
        :param args: args
        :param retry_count: retry count
        :return: {}
        """
        try:
            if not self.chatgpt_rate_limit:
                raise openai.error.RateLimitError("rate limit exceeded")

            if args is None:
                args = self.args

            response = openai.ChatCompletion.create(api_key=api_key, messages=session.messages, **args)
            logger.info("[CHATGPT] response={}".format(json.dumps(response, ensure_ascii=False, indent=4)))

            return {
                "prompt_tokens": response["usage"]["prompt_tokens"],
                "total_tokens": response["usage"]["total_tokens"],
                "completion_tokens": response["usage"]["completion_tokens"],
                "content": response.choices[0]["message"]["content"],
            }
        except Exception as e:
            need_retry = retry_count < 2
            result = {"completion_tokens": 0, "content": "我现在有点累了，等会再来吧"}
            if isinstance(e, openai.RateLimitError):
                logger.warn("[CHATGPT] RateLimitError: {}".format(e))
                result["content"] = "提问太快啦，请休息一下再问我吧"
                if need_retry:
                    time.sleep(5)
            elif isinstance(e, openai.Timeout):
                logger.warn("[CHATGPT] Timeout: {}".format(e))
                result["content"] = "我没有收到你的消息"
                if need_retry:
                    time.sleep(5)
            elif isinstance(e, openai.APIError):
                logger.warn("[CHATGPT] Bad Gateway: {}".format(e))
                result["content"] = "请再问我一次"
                if need_retry:
                    time.sleep(10)
            elif isinstance(e, openai.APIConnectionError):
                logger.warn("[CHATGPT] APIConnectionError: {}".format(e))
                result["content"] = "我连接不到你的网络"
                if need_retry:
                    time.sleep(5)
            else:
                logger.exception("[CHATGPT] Exception: {}".format(e))
                need_retry = False
                self.sessions.clear_session(session.session_id)

            if need_retry:
                logger.warn("[CHATGPT] 第{}次重试".format(retry_count + 1))
                return self.get_chat_completions(session, api_key, args, retry_count + 1)
            else:
                return result


class AzureChatGPTBot(ChatGPTBot):
    def __init__(self):
        super().__init__()
        openai.api_type = "azure"
        openai.api_version = settings.AZURE_API_VERSION or "2023-06-01-preview"
        self.args["deployment_id"] = settings.AZURE_DEPLOYMENT_ID

    def create_img(self, query, retry_count=0, api_key=None, api_base=None):
        """
        :param query: string
        :param retry_count: retry count
        :param api_key: retry api_key
        :param api_base: retry api_base
        """
        api_version = "2022-08-03-preview"
        url = "{}dalle/text-to-image?api-version={}".format(openai.api_base, api_version)
        api_key = api_key or openai.api_key
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        try:
            body = {"caption": query, "resolution": settings.IMAGE_CREATE_SIZE}
            submission = requests.post(url, headers=headers, json=body)
            operation_location = submission.headers["Operation-Location"]
            retry_after = submission.headers["Retry-after"]
            status = ""

            while status != "Succeeded":
                logger.info("waiting for image create..., " + status + ",retry after " + retry_after + " seconds")
                time.sleep(int(retry_after))
                response = requests.get(operation_location, headers=headers)
                status = response.json()["status"]

            image_url = response.json()["result"]["contentUrl"]
            return True, image_url
        except Exception as e:
            logger.error("create image error: {}".format(e))
            return False, "图片生成失败"
