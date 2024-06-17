# -*- coding: utf-8 -*-
"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
import json
import os.path
import logging

from environs import Env
from dotenv import load_dotenv

PROJECT_PATH = os.path.dirname(os.path.dirname(__file__))
os.environ["APP_ENV"] = os.environ.get("APP_ENV", "DEV")  # Set app environ [DEV, PROD]

dotenv_path = os.path.join(PROJECT_PATH, "config", ".env", os.environ["APP_ENV"].lower())
logging.warning("Project current settings path: %s", dotenv_path)
load_dotenv(dotenv_path)

env = Env()
# env.read_env()

APP_ENV = env.str("APP_ENV", default="DEV")
DEBUG = APP_ENV == "DEV"

WTF_CSRF_ENABLED = False

SECRET_KEY = env.str("SECRET_KEY", default='fr3hhj&6k2b_s&cvk(=(!#wcotx1nkcgkp%0^%no2xg#xr9^n!')
SEND_FILE_MAX_AGE_DEFAULT = env.int("SEND_FILE_MAX_AGE_DEFAULT", default=None)
BCRYPT_LOG_ROUNDS = env.int("BCRYPT_LOG_ROUNDS", default=13)
# DEBUG_TB_ENABLED = DEBUG
DEBUG_TB_ENABLED = False
DEBUG_TB_INTERCEPT_REDIRECTS = False
CACHE_TYPE = (
    "flask_caching.backends.SimpleCache"  # Can be "MemcachedCache", "RedisCache", etc.
)

SQLALCHEMY_DATABASE_URI = env.str("DATABASE_URL")
SQLALCHEMY_TRACK_MODIFICATIONS = True
SQLALCHEMY_BINDS = {
    "workflow": env.str("WORKFLOW_DATABASE_URL"),
    "novel_crawler": env.str("CRAWLER_DATABASE_URL"),
}

TIME_ZONE = None

# OpenAI Config
OPENAI_API_BASE = "http://oneapi.crotondata.cn/v1"
OPENAI_API_KEY = "sk-XpwEM1Np8oLFlEKB755445CcF06c422290F1D0D6A021977b"
OPENAI_MODEL = "gpt-4o"
OPENAI_PROXY = None
CHATGPT_RATE_LIMIT = 30
DALLE_RATE_LIMIT = 20
CONVERSATION_MAX_TOKENS = 100000
TEXT_TO_IMAGE = 'dall-e-3'
SESSION_EXPIRES_IN_SECONDS = 2 * 60 * 60

AZURE_API_VERSION = None
AZURE_DEPLOYMENT_ID = None
IMAGE_CREATE_SIZE = "256x256"

DEFAULT_OPENAI_SYSTEM_PROMPT = "你是基于大语言模型的AI智能助手，旨在回答并解决人们的任何问题，并且可以使用多种语言与人交流。"

# WorkTool Config
MAX_RETRY_TIMES = 3
WT_API_BASE = "https://api.worktool.ymdyes.cn"
WT_ROBOT_ID = env.str("WT_ROBOT_ID")
# WT_GROUP_NAMES = env.list("WT_GROUP_NAMES", subcast=str, delimiter=",")
WT_GROUP_NAMES = json.loads(env.str("WT_GROUP_NAMES"))


MIDDLEWARES = [
    "wecom.core.middlewares.authentication.AuthTokenMiddleware"
]

EXEMPT_ENDPOINTS = [
    "wecom/health_check",
]
