# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/30/21 7:50 PM
from copy import deepcopy
from functools import partial

from bson import Decimal128
from pytz import utc
from schema import Schema, Use, And

from utils.gtz import Dt, local_timezone


class EventSchema:
    @classmethod
    def type_int(cls):
        return Use(int)

    @classmethod
    def type_datetime(cls, timezone: str = local_timezone):
        return Use(partial(Dt.from_str, default_tz=timezone), partial(Dt.convert_tz, to_tz=utc))

    @classmethod
    def type_timestamp(cls):
        return lambda x: Dt.from_ts(x)

    @classmethod
    def type_decimal(cls):
        return And(Use(str), Use(Decimal128))

    @classmethod
    def parse(cls, schema: dict, ignore_extra_keys=False) -> Schema:
        """
        parse schema[str] to PythonSchema object
        :type schema: dict
            {
                "user_id": {
                    "type": "int",
                },
                "dt": {
                    "type": "datetime",
                    "timezone": "Asia/Shanghai"
                },
                "ts": {
                    "type": "timestamp"     // auto detect precision (ms or s)
                },
                "amount": {
                    "type": "decimal"
                },
            }
        :param ignore_extra_keys: bool, same arg name for Schema.ignore_extra_keys
        :return: Schema
        """
        __schema = deepcopy(schema)
        _schema = {}
        for k, v in __schema.items():
            _type = v.pop('type')
            fn = getattr(cls, f'type_{_type}')
            _schema[k] = fn(**v)
        return Schema(_schema, ignore_extra_keys=ignore_extra_keys)

    @classmethod
    def validate(cls, schema: dict, data: dict) -> dict:
        return cls.parse(schema).validate(data)
