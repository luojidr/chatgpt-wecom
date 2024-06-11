# -*- coding: utf-8 -*-
"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from environs import Env

env = Env()
env.read_env()

ENV = env.str("FLASK_ENV", default="production")
DEBUG = ENV == "development"

WTF_CSRF_ENABLED = False

SECRET_KEY = env.str("SECRET_KEY", default='fr3hhj&6k2b_s&cvk(=(!#wcotx1nkcgkp%0^%no2xg#xr9^n!')
SEND_FILE_MAX_AGE_DEFAULT = env.int("SEND_FILE_MAX_AGE_DEFAULT", default=None)
BCRYPT_LOG_ROUNDS = env.int("BCRYPT_LOG_ROUNDS", default=13)
DEBUG_TB_ENABLED = DEBUG
DEBUG_TB_INTERCEPT_REDIRECTS = False
CACHE_TYPE = (
    "flask_caching.backends.SimpleCache"  # Can be "MemcachedCache", "RedisCache", etc.
)

SQLALCHEMY_DATABASE_URI = env.str(
    "DATABASE_URL",
    default='mysql+pymysql://root:root@127.0.0.1:3306/fkcookiecutter?charset=utf8'
)
SQLALCHEMY_TRACK_MODIFICATIONS = True

TIME_ZONE = None


# OpenAI Config
OPENAI_API_BASE = "http://oneapi.crotondata.cn/v1"
OPENAI_API_KEY = "sk-XpwEM1Np8oLFlEKB755445CcF06c422290F1D0D6A021977b"
OPENAI_MODEL = None
OPENAI_PROXY = None
CHATGPT_RATE_LIMIT = None
DALLE_RATE_LIMIT = 20
CONVERSATION_MAX_TOKENS = 80000
TEXT_TO_IMAGE = 'dall-e-3'
SESSION_EXPIRES_IN_SECONDS = 2 * 60 * 60

AZURE_API_VERSION = None
AZURE_DEPLOYMENT_ID = None
IMAGE_CREATE_SIZE = "256x256"

OPENAI_SYSTEM_PROMPT = "你是基于大语言模型的AI智能助手，旨在回答并解决人们的任何问题，并且可以使用多种语言与人交流。"

# WorkTool Config
WT_API_BASE = "http://8.217.15.229:9999"
WT_ROBOTID = "d9c094fc56b649fc8688c65f565ae72e"
WT_GROUP_NAMES = ["智创Demo"]
MAX_RETRY_TIMES = 3
