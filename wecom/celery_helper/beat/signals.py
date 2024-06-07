"""Models Application signals."""
from flask_sqlalchemy.track_modifications import models_committed, before_models_committed
from sqlalchemy.event import listens_for

from .models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    SolarSchedule,
    PeriodicTask,
    PeriodicTasks
)


def signals_connect():
    """Connect to signals."""
    from .utils import settings
    if not settings.get('SQLALCHEMY_TRACK_MODIFICATIONS'):
        raise ValueError('Must set `SQLALCHEMY_TRACK_MODIFICATIONS` true')

    models_committed.connect(PeriodicTasks.changed, sender=PeriodicTask)
    before_models_committed.connect(PeriodicTasks.changed, sender=PeriodicTask)

    sender_list = [IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule]
    for sender in sender_list:
        models_committed.connect(PeriodicTasks.update_changed, sender=sender)
        before_models_committed.connect(PeriodicTasks.update_changed, sender=sender)
