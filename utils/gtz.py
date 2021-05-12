# __author__ = 'Mio'
import math
from datetime import datetime, time, timedelta, date
from typing import Union, Optional

from dateutil import parser
from pytz import utc, BaseTzInfo, timezone
# noinspection PyProtectedMember
from pytz.tzinfo import DstTzInfo
from tzlocal import get_localzone

UTC_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
SQL_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
UTC_MONTH_FORMAT = '%Y-%m'
DATE_FORMAT = "%Y-%m-%d"

local_timezone: Union[DstTzInfo, BaseTzInfo] = get_localzone()


def string_2_datetime(_string):
    if isinstance(_string, bytes):
        _string = _string.decode('utf-8')
    return parser.parse(_string)


class Dt:
    precision_ms = 13

    @classmethod
    def from_str(cls, _str, default_tz: Union[DstTzInfo, BaseTzInfo, str] = local_timezone):
        if isinstance(default_tz, str):
            default_tz = timezone(default_tz)

        dt = string_2_datetime(_str)
        if dt.tzinfo:
            dt = dt.astimezone(local_timezone)
        else:
            dt = default_tz.localize(dt)
        return dt

    @classmethod
    def from_ts(cls, ts: Union[int, str, float]):
        if isinstance(ts, str):
            ts = float(ts)

        if int(math.log10(ts) + 1) == cls.precision_ms:
            return cls.add_tz(datetime.fromtimestamp(ts / 1000), tz=utc)
        else:
            return cls.add_tz(datetime.fromtimestamp(ts), tz=utc)

    @classmethod
    def to_str(cls, dt: datetime, _format=UTC_DATETIME_FORMAT, iso_format=False):
        if iso_format:
            return dt.isoformat()
        else:
            return dt.strftime(_format)

    @classmethod
    def add_tz(cls, _dt, tz=Optional[DstTzInfo]):
        if not tz:
            tz = local_timezone
        return tz.localize(_dt)

    @classmethod
    def convert_tz(cls, _dt, to_tz: DstTzInfo, from_tz=None):
        if not _dt.tzinfo:
            _dt = cls.add_tz(_dt, from_tz)
        return to_tz.normalize(_dt)

    @classmethod
    def now(cls, tz=local_timezone):
        return datetime.now(tz=tz)

    @classmethod
    def utc_now(cls):
        return datetime.now(tz=utc)

    @classmethod
    def to_ts(cls, _dt: datetime, from_tz=None, to_tz=utc) -> float:
        """
        转换为utc的时间戳
        如果有时区的datetime转换为ts会变成当前时区的ts，所以这里会先转换为utc时区再得到ts
        :param _dt:
        :param from_tz: 如果_dt没有时区信息则默认None为本地时区
        :param to_tz: _dt转换为该时区
        :return: utc timestamp
        """
        _dt = cls.convert_tz(_dt, to_tz=to_tz, from_tz=from_tz)
        return _dt.replace(tzinfo=None).timestamp()

    @classmethod
    def now_ts(cls) -> float:
        return datetime.utcnow().timestamp()


class Date(Dt):
    @classmethod
    def from_str(cls, *args, **kwargs):
        dt = super(Date, cls).from_str(*args, **kwargs)
        return dt.date()

    @classmethod
    def to_str(cls, _date: date, _format=DATE_FORMAT, iso_format=False):
        if iso_format:
            return _date.isoformat()
        else:
            return _date.strftime(_format)

    @classmethod
    def today(cls, tz=local_timezone):
        return Dt.now(tz=tz).date()

    @classmethod
    def utc_today(cls):
        return cls.today(tz=utc)

    @classmethod
    def to_dt(cls, _date, tz: Optional[DstTzInfo]):
        dt = datetime.combine(_date, time.min)
        if tz:
            dt = cls.add_tz(dt, tz=tz)
        return dt


def local_date_2_utc_dt(_date, tz=local_timezone):
    return Dt.convert_tz(Date.to_dt(_date, tz=tz), to_tz=utc)


def local_dt_2_utc_dt(_dt: datetime, local_tz=local_timezone):
    return Dt.convert_tz(_dt, to_tz=utc, from_tz=local_tz)


local_yesterday = Date.today() - timedelta(days=1)


def utc_now_dt_str():
    return Dt.to_str(Dt.utc_now())
