from flask import Blueprint

from . import models
from .signals import signals_connect

signals_connect()
blueprint = Blueprint("beat", __name__)
