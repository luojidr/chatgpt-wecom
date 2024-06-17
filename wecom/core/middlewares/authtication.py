import logging
import time
import traceback
from typing import List, Dict, Union

from flask import Flask
from flask import request, jsonify, Response
from werkzeug import exceptions
from flask_jwt_extended import verify_jwt_in_request, current_user

from .base import BaseMiddleware
from ...utils.crypto import AESCipher

EXEMPT_METHODS = ["OPTIONS"]


class AuthTokenMiddleware(BaseMiddleware):
    def __init__(self, app: Flask):
        super().__init__(app=app)

    def authenticate(self) -> Union[None, Response]:
        try:
            # header: Authorization
            authorization = request.headers.get("Authorization")
            logging.info("Authorization: %s", authorization)

            verify_jwt_in_request()
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return jsonify(status=5000, msg="invalid token or token is expired", data=None)

        args = (request.path, request.method, current_user.user_id, current_user.user_name)
        self.logger.info("Path: %s, Method: %s, Current user: user_id: %s, username: %s", *args)

    def deprecated__call__(self, *args, **kwargs):
        self.logger.info("AuthTokenMiddleware >>> path: %s, method: %s", request.path, request.method)

        if request.method in EXEMPT_METHODS:
            return

        payload: dict = {}
        request_path: str = request.path
        content_type: str = request.content_type or ""

        if "application/json" in content_type.lower():
            payload: dict = request.json

        endpoint_func: str = payload.get("path")
        exempt_paths: Dict[str, List[str]] = self.exempt_paths

        # root route path
        if endpoint_func and endpoint_func in exempt_paths["params_paths"]:
            self.logger.info("AuthTokenMiddleware exempt endpoint func by root, path: %s", endpoint_func)
            return

        # normal request path
        if request_path in exempt_paths["request_paths"]:
            self.logger.info("AuthTokenMiddleware exempt request, path: %s", request_path)
            return

        # distinguish web request, or not service invoke
        if "X-Token" in request.headers:
            x_token = request.headers["X-Token"]
            plain_text = AESCipher(key=self.settings.DEFAULT_AES_KEY).decrypt(x_token)
            secret, timestamp, name = plain_text.split(":")

            if secret != self.settings.DEFAULT_AES_SECRET:
                raise ValueError("service token error in service internal call.")

            if int(time.time()) > int(timestamp):
                raise ValueError("service token is expired.")

            if name != self.settings.DEFAULT_AES_APP:
                raise ValueError("illegal application call.")

            return

        # verify the user JWT token
        result = self.authenticate()
        return result

    def __call__(self, *args, **kwargs):
        pass
