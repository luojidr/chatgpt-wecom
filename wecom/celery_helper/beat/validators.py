"""Validators."""
import operator
import crontab

from .utils import make_hashable

NON_FIELD_ERRORS = "__all__"


class ValidationError(Exception):
    """An error while validating data."""

    def __init__(self, message, code=None, params=None):
        """
        The `message` argument can be a single error, a list of errors, or a
        dictionary that maps field names to lists of errors. What we define as
        an "error" can be either a simple string or an instance of
        ValidationError with its message attribute set, and what we define as
        list or dictionary can be an actual `list` or `dict` or an instance
        of ValidationError with its `error_list` or `error_dict` attribute set.
        """
        super().__init__(message, code, params)

        if isinstance(message, ValidationError):
            if hasattr(message, "error_dict"):
                message = message.error_dict
            elif not hasattr(message, "message"):
                message = message.error_list
            else:
                message, code, params = message.message, message.code, message.params

        if isinstance(message, dict):
            self.error_dict = {}
            for field, messages in message.items():
                if not isinstance(messages, ValidationError):
                    messages = ValidationError(messages)
                self.error_dict[field] = messages.error_list

        elif isinstance(message, list):
            self.error_list = []
            for message in message:
                # Normalize plain strings to instances of ValidationError.
                if not isinstance(message, ValidationError):
                    message = ValidationError(message)
                if hasattr(message, "error_dict"):
                    self.error_list.extend(sum(message.error_dict.values(), []))
                else:
                    self.error_list.extend(message.error_list)

        else:
            self.message = message
            self.code = code
            self.params = params
            self.error_list = [self]

    @property
    def message_dict(self):
        # Trigger an AttributeError if this ValidationError
        # doesn't have an error_dict.
        getattr(self, "error_dict")

        return dict(self)

    @property
    def messages(self):
        if hasattr(self, "error_dict"):
            return sum(dict(self).values(), [])
        return list(self)

    def update_error_dict(self, error_dict):
        if hasattr(self, "error_dict"):
            for field, error_list in self.error_dict.items():
                error_dict.setdefault(field, []).extend(error_list)
        else:
            error_dict.setdefault(NON_FIELD_ERRORS, []).extend(self.error_list)
        return error_dict

    def __iter__(self):
        if hasattr(self, "error_dict"):
            for field, errors in self.error_dict.items():
                yield field, list(ValidationError(errors))
        else:
            for error in self.error_list:
                message = error.message
                if error.params:
                    message %= error.params
                yield str(message)

    def __str__(self):
        if hasattr(self, "error_dict"):
            return repr(dict(self))
        return repr(list(self))

    def __repr__(self):
        return "ValidationError(%s)" % self

    def __eq__(self, other):
        if not isinstance(other, ValidationError):
            return NotImplemented
        return hash(self) == hash(other)

    def __hash__(self):
        if hasattr(self, "message"):
            return hash(
                (
                    self.message,
                    self.code,
                    make_hashable(self.params),
                )
            )
        if hasattr(self, "error_dict"):
            return hash(make_hashable(self.error_dict))
        return hash(tuple(sorted(self.error_list, key=operator.attrgetter("message"))))


class _CronSlices(crontab.CronSlices):
    """Cron slices with customized validation."""

    def __init__(self, *args):
        super(crontab.CronSlices, self).__init__(
            [_CronSlice(info) for info in crontab.S_INFO]
        )
        self.special = None
        self.setall(*args)
        self.is_valid = self.is_self_valid

    @classmethod
    def validate(cls, *args):
        try:
            cls(*args)
        except Exception as e:
            raise ValueError(e)


class _CronSlice(crontab.CronSlice):
    """Cron slice with custom range parser."""

    def get_range(self, *vrange):
        ret = _CronRange(self, *vrange)
        if ret.dangling is not None:
            return [ret.dangling, ret]
        return [ret]


class _CronRange(crontab.CronRange):
    """Cron range parser class."""

    # rewrite whole method to raise error on bad range
    def parse(self, value):
        if value.count('/') == 1:
            value, seq = value.split('/')
            try:
                self.seq = self.slice.parse_value(seq)
            except crontab.SundayError:
                self.seq = 1
                value = "0-0"
            if self.seq < 1 or self.seq > self.slice.max:
                raise ValueError("Sequence can not be divided by zero or max")
        if value.count('-') == 1:
            vfrom, vto = value.split('-')
            self.vfrom = self.slice.parse_value(vfrom, sunday=0)
            try:
                self.vto = self.slice.parse_value(vto)
            except crontab.SundayError:
                if self.vfrom == 1:
                    self.vfrom = 0
                else:
                    self.dangling = 0
                self.vto = self.slice.parse_value(vto, sunday=6)
            if self.vto < self.vfrom:
                raise ValueError("Bad range '{0.vfrom}-{0.vto}'".format(self))
        elif value == '*':
            self.all()
        else:
            raise ValueError('Unknown cron range value "%s"' % value)


def crontab_validator(value):
    """Validate crontab."""
    try:
        _CronSlices.validate(value)
    except ValueError as e:
        raise ValidationError(e)


def minute_validator(value):
    """Validate minutes crontab value."""
    _validate_crontab(value, 0)


def hour_validator(value):
    """Validate hours crontab value."""
    _validate_crontab(value, 1)


def day_of_month_validator(value):
    """Validate day of month crontab value."""
    _validate_crontab(value, 2)


def month_of_year_validator(value):
    """Validate month crontab value."""
    _validate_crontab(value, 3)


def day_of_week_validator(value):
    """Validate day of week crontab value."""
    _validate_crontab(value, 4)


def _validate_crontab(value, index):
    tab = ['*'] * 5
    tab[index] = value
    tab = ' '.join(tab)
    crontab_validator(tab)
