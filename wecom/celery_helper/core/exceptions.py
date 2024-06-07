
class CeleryError(Exception):
    """Base class for all Flask Celery errors."""


class CeleryVersionError(CeleryError):
    """ Celery version error. """


class ImproperlyConfigured(CeleryError):
    """ improperly configured"""
    pass
