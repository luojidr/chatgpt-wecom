from flask import Flask
from .base import BaseMiddleware


class PermissionMiddleware(BaseMiddleware):
	def __init__(self, app: Flask):
		super().__init__(app)
