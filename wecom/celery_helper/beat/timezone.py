"""
Timezone-related classes and functions.
"""

import functools
import zoneinfo
from contextlib import ContextDecorator
from datetime import datetime, timedelta, timezone, tzinfo

from asgiref.local import Local

__all__ = [
    "get_default_timezone",
    "get_current_timezone",
    "localtime",
    "now",
    "is_aware",
    "is_naive",
    "make_aware",
]


# In order to avoid accessing settings at compile time,
# wrap the logic in a function and cache the result.
@functools.lru_cache
def get_default_timezone():
    """
    Return the default time zone as a tzinfo instance.

    This is the time zone defined by settings.TIME_ZONE.
    """
    from .utils import settings
    return zoneinfo.ZoneInfo(settings.TIME_ZONE)


_active = Local()


def get_current_timezone():
    """Return the currently active time zone as a tzinfo instance."""
    return getattr(_active, "value", get_default_timezone())


# Timezone selection functions.

# These functions don't change os.environ['TZ'] and call time.tzset()
# because it isn't thread safe.


def localtime(value=None, timezone=None):
    """
    Convert an aware datetime.datetime to local time.

    Only aware datetimes are allowed. When value is omitted, it defaults to
    now().

    Local time is defined by the current time zone, unless another time zone
    is specified.
    """
    if value is None:
        value = now()
    if timezone is None:
        timezone = get_current_timezone()
    # Emulate the behavior of astimezone() on Python < 3.6.
    if is_naive(value):
        raise ValueError("localtime() cannot be applied to a naive datetime")
    return value.astimezone(timezone)


def now():
    """
    Return an aware or naive datetime.datetime, depending on settings.USE_TZ.
    """
    from .utils import settings
    return datetime.now(tz=timezone.utc if settings.USE_TZ else None)


# By design, these four functions don't perform any checks on their arguments.
# The caller should ensure that they don't receive an invalid value like None.


def is_aware(value):
    """
    Determine if a given datetime.datetime is aware.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def is_naive(value):
    """
    Determine if a given datetime.datetime is naive.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is None


def make_aware(value, timezone=None):
    """Make a naive datetime.datetime in a given time zone aware."""
    if timezone is None:
        timezone = get_current_timezone()
    # Check that we won't overwrite the timezone of an aware datetime.
    if is_aware(value):
        raise ValueError("make_aware expects a naive datetime, got %s" % value)
    # This may be wrong around DST changes!
    return value.replace(tzinfo=timezone)

