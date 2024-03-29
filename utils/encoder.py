# coding=utf-8
# __author__ = 'Mio'
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from json import JSONEncoder
from typing import Union, Optional
from uuid import UUID
import json

from aiocache.serializers import BaseSerializer
from bson import ObjectId, Decimal128
from odmantic.model import ObjectId as odObjectID

unicode_type = str
_TO_UNICODE_TYPES = (unicode_type, type(None))


def to_unicode(value: Union[None, str, bytes]) -> Optional[str]:  # noqa: F811
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, _TO_UNICODE_TYPES):
        return value
    if not isinstance(value, bytes):
        raise TypeError("Expected bytes, unicode, or None; got %r" % type(value))
    return value.decode("utf-8")


def g_str(string):
    return to_unicode(string).strip()


class MyEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        if isinstance(o, defaultdict):
            return dict(o)
        if isinstance(o, Enum):
            return o.value
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, timedelta):
            return o.total_seconds()
        # if isinstance(o, SQLAlchemyError):
        #     return str(o)
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, (ObjectId, odObjectID)):
            return str(o)
        if isinstance(o, (Decimal128, Decimal)):
            return str(o)

        return JSONEncoder.default(self, o)


class JsonSerializer(BaseSerializer):
    """
    Transform data to json string with json.dumps and json.loads to retrieve it back. Check
    https://docs.python.org/3/library/json.html#py-to-json-table for how types are converted.

    ujson will be used by default if available. Be careful with differences between built in
    json module and ujson:
        - ujson dumps supports bytes while json doesn't
        - ujson and json outputs may differ sometimes
    """

    def dumps(self, value):
        """
        Serialize the received value using ``json.dumps``.

        :param value: dict
        :returns: str
        """
        return json.dumps(value, cls=MyEncoder)

    def loads(self, value):
        """
        Deserialize value using ``json.loads``.

        :param value: str
        :returns: output of ``json.loads``.
        """
        if value is None:
            return None
        return json.loads(value)


