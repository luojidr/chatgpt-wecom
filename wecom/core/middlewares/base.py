import logging
from flask import Flask, url_for
from functools import cached_property
from typing import List, Dict

from .. import config
from ..utils import get_user


class BaseMiddleware:
	def __init__(self, app: Flask, logger=None):
		self.app = app
		self._logger = logger or logging.getLogger(__name__)

	@cached_property
	def settings(self):
		return config

	@property
	def logger(self):
		return self._logger

	@logger.setter
	def logger(self, value):
		self._logger = value

	@cached_property
	def exempt_paths(self) -> Dict[str, List[str]]:
		""" Standard like this, eg.
			[url_for(endpoint=endpoint) for endpoint in self.settings.EXEMPT_ENDPOINTS]
		"""
		# 统计所有需要豁免的端点，否则会有问题
		exempt_paths: Dict[str, List[str]] = {}

		for endpoint in self.settings.EXEMPT_ENDPOINTS:
			if endpoint[0].isupper() and "__" in endpoint:
				exempt_paths.setdefault("params_paths", []).append(endpoint)  # like 'UserInfoAPI__login'
			else:
				request_path = url_for(endpoint=endpoint)
				exempt_paths.setdefault("request_paths", []).append(request_path)

		return exempt_paths

	def _get_user(self, userid: str):
		return get_user(userid=userid)




