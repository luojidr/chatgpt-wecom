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
SQLALCHEMY_ECHO = DEBUG

TIME_ZONE = None

# OpenAI Config
OPENAI_API_BASE = env.str("OPENAI_API_BASE")
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
OPENAI_MODEL = env.str("LLM_MODEL")
OPENAI_PROXY = None
CHATGPT_RATE_LIMIT = 30
DALLE_RATE_LIMIT = 0
CONVERSATION_MAX_TOKENS = 100000
TEXT_TO_IMAGE = 'dall-e-3'
SESSION_EXPIRES_IN_SECONDS = 2 * 60 * 60

AZURE_API_VERSION = None
AZURE_DEPLOYMENT_ID = None
IMAGE_CREATE_SIZE = "256x256"


# WeCom Config
MAX_RETRY_TIMES = 3
WT_API_BASE = env.str("WT_API_BASE")
WT_ROBOT_ID = env.str("WT_ROBOT_ID")
WT_GROUP_MASTER = "元进"

MIDDLEWARES = [
    "wecom.core.middlewares.authentication.AuthTokenMiddleware"
]

EXEMPT_ENDPOINTS = [
    "wecom/health_check",
]
