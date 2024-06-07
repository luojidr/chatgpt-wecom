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
