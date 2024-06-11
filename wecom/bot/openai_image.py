import json
import time

import openai

from wecom.core.log import logger
from wecom.core.token_bucket import TokenBucket
from config import settings


# OPENAI提供的画图接口
class OpenAIImage(object):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if settings.DALLE_RATE_LIMIT:
            self.tb4dalle = TokenBucket(settings.DALLE_RATE_LIMIT or 20)

    def create_img(self, query, retry_count=0, api_key=None, api_base=None):
        revised_prompt = None

        try:
            if settings.DALLE_RATE_LIMIT and not self.tb4dalle.get_token():
                return False, "请求太快了，请休息一下再问我吧"

            logger.info("[OPEN_AI] image_query={}".format(query))
            response = openai.Image.create(
                api_key=api_key,
                prompt=query,  # 图片描述
                n=1,  # 每次生成图片的数量
                model=settings.TEXT_TO_IMAGE or "dall-e-2",
                # size=settings.IMAGE_CREATE_SIZE or "256x256",  # 图片大小,可选有 256x256, 512x512, 1024x1024
            )
            image_url = response["data"][0]["url"]
            revised_prompt = response["data"][0]["revised_prompt"]

            logger.info("[OPEN_AI] image_url={}".format(image_url))
            return True, image_url, revised_prompt
        except openai.RateLimitError as e:
            logger.warn(e)
            if retry_count < 1:
                time.sleep(5)
                logger.warn("[OPEN_AI] ImgCreate RateLimit exceed, 第{}次重试".format(retry_count + 1))
                return self.create_img(query, retry_count + 1)
            else:
                return False, "画图出现问题，请休息一下再问我吧", revised_prompt
        except Exception as e:
            logger.exception(e)
            return False, "画图出现问题，请休息一下再问我吧", revised_prompt
