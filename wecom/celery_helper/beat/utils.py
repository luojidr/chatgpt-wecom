"""Utilities."""
from importlib import import_module

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from . import timezone

is_aware = timezone.is_aware
# celery schedstate return None will make it not work
NEVER_CHECK_TIMEOUT = 100000000

# see Issue #222
now_localtime = getattr(timezone, 'template_localtime', timezone.localtime)


class LookupFlaskApp:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = object.__new__(cls, *args, **kwargs)

            app = Flask('flask_celery_helper')
            app.config.from_object('config.settings')

            db = SQLAlchemy()
            db.init_app(app)

            cls._instance.app = app

        return cls._instance.app


def make_aware(value):
    """Force datatime to have timezone information."""
    if getattr(settings, 'USE_TZ', False):
        # naive datetimes are assumed to be in UTC.
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.utc)
        # then convert to the Django configured timezone.
        default_tz = timezone.get_default_timezone()
        value = timezone.localtime(value, default_tz)
    else:
        # naive datetimes are assumed to be in local timezone.
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_default_timezone())
    return value


def now():
    """Return the current date and time."""
    if getattr(settings, 'USE_TZ', False):
        return now_localtime(timezone.now())
    else:
        return timezone.now()


def is_database_scheduler(scheduler):
    """Return true if Celery is configured to use the db scheduler."""
    if not scheduler:
        return False
    from kombu.utils import symbol_by_name

    from .schedulers import DatabaseScheduler
    return (
        scheduler == 'flask'
        or issubclass(symbol_by_name(scheduler), DatabaseScheduler)
    )


def is_iterable(x):
    "An implementation independent way of checking for iterables"
    try:
        iter(x)
    except TypeError:
        return False
    else:
        return True


def make_hashable(value):
    """
    Attempt to make value hashable or raise a TypeError if it fails.

    The returned value should generate the same hash for equal values.
    """
    if isinstance(value, dict):
        return tuple(
            [
                (key, make_hashable(nested_value))
                for key, nested_value in sorted(value.items())
            ]
        )
    # Try hash to avoid converting a hashable iterable (e.g. string, frozenset)
    # to a tuple.
    try:
        hash(value)
    except TypeError:
        if is_iterable(value):
            return tuple(map(make_hashable, value))
        # Non-hashable, non-iterable.
        raise
    return value


flask_app = LookupFlaskApp()
settings = flask_app.config
