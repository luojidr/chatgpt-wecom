"""Database models."""
try:
    from zoneinfo import available_timezones
except ImportError:
    from backports.zoneinfo import available_timezones

import os
from datetime import timedelta

from celery import schedules
from cron_descriptor import get_description
from flask import current_app as flask_app

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from .clockedschedule import clocked
from .tzcrontab import TzAwareCrontab
from .utils import make_aware, now, flask_app

DAYS = 'days'
HOURS = 'hours'
MINUTES = 'minutes'
SECONDS = 'seconds'
MICROSECONDS = 'microseconds'

PERIOD_CHOICES = (
    (DAYS, "天"),
    (HOURS, "小时"),
    (MINUTES, "分钟"),
    (SECONDS, "秒"),
    (MICROSECONDS, "毫秒"),
)

SINGULAR_PERIODS = (
    (DAYS, "天"),
    (HOURS, "小时"),
    (MINUTES, "分钟"),
    (SECONDS, "秒"),
    (MICROSECONDS, "毫秒"),
)

SOLAR_SCHEDULES = [
    ("dawn_astronomical", "天文黎明"),
    ("dawn_civil", "民事黎明"),
    ("dawn_nautical", "航海黎明"),
    ("dusk_astronomical", "天文黄昏"),
    ("dusk_civil", "民事黄昏"),
    ("dusk_nautical", "航海黄昏"),
    ("solar_noon", "正午"),
    ("sunrise", "日出"),
    ("sunset", "日落"),
]

db = flask_app.extensions["sqlalchemy"]


def cronexp(field):
    """Representation of cron expression."""
    return field and str(field).replace(' ', '') or '*'


def crontab_schedule_celery_timezone():
    """Return timezone string from Django settings ``CELERY_TIMEZONE`` variable.

    If is not defined or is not a valid timezone, return ``"UTC"`` instead.
    """  # noqa: E501
    celery_timezone = os.environ.get('TIMEZONE')
    if celery_timezone in available_timezones():
        return celery_timezone
    return 'UTC'


class SolarSchedule(db.Model):
    """Schedule following astronomical patterns.

    Example: to run every sunrise in New York City:

    >>> event='sunrise', latitude=40.7128, longitude=74.0060
    """
    __tablename__ = "celery_beat_solarschedule"
    __table_args__ = tuple(db.UniqueConstraint('name', 'address'))

    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(24), nullable=False, comment="Solar Event")
    latitude = db.Column(db.DECIMAL(9, 6), nullable=False, comment="Latitude")
    longitude = db.Column(db.DECIMAL(9, 6), nullable=False, comment="Longitude")

    @property
    def schedule(self):
        return schedules.solar(
            self.event,
            self.latitude,
            self.longitude,
            nowfun=lambda: make_aware(now())
        )

    @classmethod
    def from_schedule(cls, schedule):
        spec = {'event': schedule.event,
                'latitude': schedule.lat,
                'longitude': schedule.lon}

        # we do not check for MultipleResultsFound exception here because
        # the unique_together constraint safely prevents from duplicates
        instance = cls.objects.filter_by(**spec).first()
        if instance is None:
            instance = cls(**spec)
            db.session.add(instance)
            db.session.commit()

        return instance

    def __str__(self):
        return '{} ({}, {})'.format(
            self.get_event_display(),
            self.latitude,
            self.longitude
        )


class IntervalSchedule(db.Model):
    """Schedule executing on a regular interval.

    Example: execute every 2 days:

    >>> every=2, period=DAYS
    """
    __tablename__ = "celery_beat_intervalschedule"

    DAYS = DAYS
    HOURS = HOURS
    MINUTES = MINUTES
    SECONDS = SECONDS
    MICROSECONDS = MICROSECONDS

    PERIOD_CHOICES = PERIOD_CHOICES

    id = db.Column(db.Integer, primary_key=True)
    every = db.Column(db.Integer, nullable=False, default=1, comment='Number of Periods')
    period = db.Column(db.Enum(*[v[0] for v in PERIOD_CHOICES]), nullable=False, comment='Interval Period')

    @property
    def schedule(self):
        return schedules.schedule(
            timedelta(**{self.period: self.every}),
            nowfun=lambda: make_aware(now())
        )

    @classmethod
    def from_schedule(cls, schedule, period=SECONDS):
        every = max(schedule.run_every.total_seconds(), 0)
        instance = cls.query.filter_by(every=every, period=period).first()

        if instance is None:
            instance = cls(every=every, period=period)
            db.session.add(instance)
            db.session.commit()

        return instance

    def __str__(self):
        readable_period = None
        if self.every == 1:
            for period, _readable_period in SINGULAR_PERIODS:
                if period == self.period:
                    readable_period = _readable_period.lower()
                    break
            return 'every {}'.format(readable_period)
        for period, _readable_period in PERIOD_CHOICES:
            if period == self.period:
                readable_period = _readable_period.lower()
                break
        return 'every {} {}'.format(self.every, readable_period)

    @property
    def period_singular(self):
        return self.period[:-1]


class ClockedSchedule(db.Model):
    """clocked schedule."""
    __tablename__ = 'celery_beat_clockedschedule'

    id = db.Column(db.Integer, primary_key=True)
    clocked_time = db.Column(db.DateTime, nullable=False, comment="Clock Time")

    def __str__(self):
        return f'{make_aware(self.clocked_time)}'

    @property
    def schedule(self):
        c = clocked(clocked_time=self.clocked_time)
        return c

    @classmethod
    def from_schedule(cls, schedule):
        spec = {'clocked_time': schedule.clocked_time}
        instance = cls.query.filter_by(**spec).first()

        if instance is None:
            instance = cls(**spec)
            db.session.add(instance)
            db.session.commit()

        return instance


class CrontabSchedule(db.Model):
    """Timezone Aware Crontab-like schedule.

    Example:  Run every hour at 0 minutes for days of month 10-15:

    >>> minute="0", hour="*", day_of_week="*",
    ... day_of_month="10-15", month_of_year="*"
    """

    #
    # The worst case scenario for day of month is a list of all 31 day numbers
    # '[1, 2, ..., 31]' which has a length of 115. Likewise, minute can be
    # 0..59 and hour can be 0..23. Ensure we can accomodate these by allowing
    # 4 chars for each value (what we save on 0-9 accomodates the []).
    # We leave the other fields at their historical length.
    #
    __tablename__ = "celery_beat_crontabschedule"

    id = db.Column(db.Integer, primary_key=True)
    minute = db.Column(db.String(40 * 6), nullable=False, default='*', comment="Minute(s)")
    hour = db.Column(db.String(24 * 4), nullable=False, default='*', comment="Hour(s)")
    day_of_week = db.Column(db.String(64), nullable=False, default='*', comment="Day(s) Of The Week")
    day_of_month = db.Column(db.String(31 * 4), nullable=False, default='*', comment="Day(s) Of The Month")
    month_of_year = db.Column(db.String(64), nullable=False, default='*', comment="Month(s) Of The Year")
    timezone = db.Column(db.String(128), nullable=False, default=crontab_schedule_celery_timezone, comment="Cron Timezone")

    @property
    def human_readable(self):
        human_readable = get_description('{} {} {} {} {}'.format(
            cronexp(self.minute), cronexp(self.hour),
            cronexp(self.day_of_month), cronexp(self.month_of_year),
            cronexp(self.day_of_week)
        ))
        return f'{human_readable} {str(self.timezone)}'

    def __str__(self):
        return '{} {} {} {} {} (m/h/dM/MY/d) {}'.format(
            cronexp(self.minute), cronexp(self.hour),
            cronexp(self.day_of_month), cronexp(self.month_of_year),
            cronexp(self.day_of_week), str(self.timezone)
        )

    @property
    def schedule(self):
        crontab = schedules.crontab(
            minute=self.minute,
            hour=self.hour,
            day_of_week=self.day_of_week,
            day_of_month=self.day_of_month,
            month_of_year=self.month_of_year,
        )
        if getattr(flask_app.config, 'DJANGO_CELERY_BEAT_TZ_AWARE', True):
            crontab = TzAwareCrontab(
                minute=self.minute,
                hour=self.hour,
                day_of_week=self.day_of_week,
                day_of_month=self.day_of_month,
                month_of_year=self.month_of_year,
                tz=self.timezone
            )
        return crontab

    @classmethod
    def from_schedule(cls, schedule):
        spec = {'minute': schedule._orig_minute,
                'hour': schedule._orig_hour,
                'day_of_week': schedule._orig_day_of_week,
                'day_of_month': schedule._orig_day_of_month,
                'month_of_year': schedule._orig_month_of_year,
                'timezone': schedule.tz
                }
        instance = cls.query.filter_by(**spec).first()

        if instance is None:
            instance = cls(**spec)
            db.session.add(instance)
            db.session.commit()

        return instance


class PeriodicTasks(db.Model):
    """Helper table for tracking updates to periodic tasks.

    This stores a single row with ``ident=1``. ``last_update`` is updated via
    signals whenever anything changes in the :class:`~.PeriodicTask` model.
    Basically this acts like a DB data audit trigger.
    Doing this so we also track deletions, and not just insert/update.
    """
    __tablename__ = "celery_beat_periodictasks"

    ident = db.Column(db.SmallInteger, nullable=False, default=1, primary_key=True)
    last_update = db.Column(db.DateTime, nullable=False)

    @classmethod
    def changed(cls, instance, **kwargs):
        if not instance.no_changes:
            cls.update_changed()

    @classmethod
    def update_changed(cls, **kwargs):
        instance = cls.query.get(**{"ident": 1})
        if instance is None:
            instance = cls(ident=1, last_update=now())
        else:
            instance.last_update = now()

        db.session.add(instance)
        db.session.commit()

    @classmethod
    def last_change(cls):
        instance = cls.query.filter_by(**{"ident": 1}).first()
        if instance:
            return instance.no_changes


class PeriodicTask(db.Model):
    """Model representing a periodic task."""
    __tablename__ = "celery_beat_periodictask"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True, comment="Name")
    task = db.Column(db.String(200), nullable=False, comment="Task Name")

    # You can only set ONE of the following schedule FK's
    interval_id = db.Column(
        db.Integer,
        ForeignKey("celery_beat_intervalschedule.id", ondelete='SET NULL'),
        nullable=True, comment="Interval Schedule"
    )
    crontab_id = db.Column(
        db.Integer,
        ForeignKey("celery_beat_crontabschedule.id", ondelete='SET NULL'),
        nullable=True, comment="Crontab Schedule"
    )
    solar_id = db.Column(
        db.Integer,
        ForeignKey("celery_beat_solarschedule.id", ondelete='SET NULL'),
        nullable=True, comment="Solar Schedule"
    )
    clocked_id = db.Column(
        db.Integer,
        ForeignKey("celery_beat_clockedschedule.id", ondelete='SET NULL'),
        nullable=True, comment="Clocked Schedule"
    )

    args = db.Column(db.JSON, nullable=False, default="[]", comment="Positional Arguments")
    kwargs = db.Column(db.JSON, nullable=False, default="{}", comment="Keyword Arguments")
    queue = db.Column(db.String(200), nullable=True, default=None, comment="Queue Override")
    exchange = db.Column(db.String(200), nullable=True, default=None, comment="Exchange")
    routing_key = db.Column(db.String(200), nullable=True, default=None, comment="Routing Key")
    headers = db.Column(db.JSON, nullable=False, default="{}", comment="AMQP Message Headers")
    # Priority Number between 0 and 255.Supported by: RabbitMQ, Redis (priority reversed, 0 is highest).
    priority = db.Column(db.Integer, nullable=True, default=None, comment="Priority")
    expires = db.Column(db.DateTime, nullable=True, default=None, comment="Expires Datetime")
    expire_seconds = db.Column(db.Integer, nullable=True, default=None, comment="Expires timedelta with seconds")
    one_off = db.Column(db.Boolean, nullable=False, default=False, comment="One-off Task")
    start_time = db.Column(db.DateTime, nullable=True, default=None, comment="Start Datetime")
    enabled = db.Column(db.Boolean, nullable=False, default=True, comment="Enabled")
    last_run_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now(), comment="Last Run Datetime")
    total_run_count = db.Column(db.Integer, nullable=False, default=0, comment="Total Run Count")
    date_changed = db.Column(db.DateTime, onupdate=func.now(), comment="Last Modified")
    description = db.Column(db.Text, nullable=False, default="", comment="Description")

    no_changes = False

    #
    # def validate_unique(self, *args, **kwargs):
    #     super().validate_unique(*args, **kwargs)
    #
    #     schedule_types = ['interval', 'crontab', 'solar', 'clocked']
    #     selected_schedule_types = [s for s in schedule_types
    #                                if getattr(self, s)]
    #
    #     if len(selected_schedule_types) == 0:
    #         raise ValidationError(
    #             'One of clocked, interval, crontab, or solar '
    #             'must be set.'
    #         )
    #
    #     err_msg = 'Only one of clocked, interval, crontab, '\
    #         'or solar must be set'
    #     if len(selected_schedule_types) > 1:
    #         error_info = {}
    #         for selected_schedule_type in selected_schedule_types:
    #             error_info[selected_schedule_type] = [err_msg]
    #         raise ValidationError(error_info)
    #
    #     # clocked must be one off task
    #     if self.clocked and not self.one_off:
    #         err_msg = 'clocked must be one off, one_off must set True'
    #         raise ValidationError(err_msg)

    @classmethod
    def get_enabled(cls):
        return cls.query.filter_by(enabled=True).all()

    def save(self, *args, **kwargs):
        self.exchange = self.exchange or None
        self.routing_key = self.routing_key or None
        self.queue = self.queue or None
        self.headers = self.headers or None
        if not self.enabled:
            self.last_run_at = None
        self._clean_expires()
        self.validate_unique()

        db.session.add(self)
        db.session.commit()
        PeriodicTasks.changed(self)

    def delete(self, *args, **kwargs):
        db.session.delete(self)
        db.session.commit()
        PeriodicTasks.changed(self)

    def _clean_expires(self):
        if self.expire_seconds is not None and self.expires:
            raise ValueError('Only one can be set, in expires and expire_seconds')

    @property
    def expires_(self):
        return self.expires or self.expire_seconds

    def __str__(self):
        fmt = '{0.name}: {{no schedule}}'
        if self.interval:
            fmt = '{0.name}: {0.interval}'
        if self.crontab:
            fmt = '{0.name}: {0.crontab}'
        if self.solar:
            fmt = '{0.name}: {0.solar}'
        if self.clocked:
            fmt = '{0.name}: {0.clocked}'
        return fmt.format(self)

    @property
    def scheduler(self):
        ident = None
        Model = None

        if self.interval_id:
            Model = IntervalSchedule
            ident = self.interval_id
        if self.crontab_id:
            Model = CrontabSchedule
            ident = self.crontab_id
        if self.solar_id:
            Model = SolarSchedule
            ident = self.solar_id
        if self.clocked_id:
            Model = ClockedSchedule
            ident = self.clocked_id

        return Model.query.filter_by(id=ident).first()


    @property
    def schedule(self):
        return self.scheduler.schedule
