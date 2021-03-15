# coding=utf-8
# __author__ = 'Mio'
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from json import JSONEncoder
from uuid import UUID

# from sqlalchemy.exc import SQLAlchemyError
from bson import ObjectId
from tornado.escape import native_str


def g_str(string):
    return native_str(string).strip()


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
        if isinstance(o, ObjectId):
            return str(o)

        return JSONEncoder.default(self, o)
