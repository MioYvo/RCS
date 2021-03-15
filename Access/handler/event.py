import json
from abc import ABC

from schema import Schema, SchemaError, Optional as SchemaOptional, Use, And
from jsonschema import validate
from jsonschema.exceptions import SchemaError as JSONSchemaError
from jsonschema.validators import validator_for

from Access.clients import event_collection
from Access.handler.validator import Event
from Access.settings import AccessExchangeName, EVENT_ROUTING_KEY
from utils.mbson import convert_json_schema_to_son
from utils.gtz import Dt
from utils.mongo_paginate import paginate
from utils.web import BaseRequestHandler


class EventHandler(BaseRequestHandler, ABC):
    async def get(self):
        """
        @api {get} /event Event List
        @apiName GetEvent
        @apiGroup Event

        @apiParam {String} sort="" 排序键名
        @apiParam {String="0", "1"} desc="1" 是否倒序
        @apiParam {String} name="" 搜索事件名字

        @apiSuccess {String} error_code code of error from error code table.
        @apiSuccess {String} message message.
        @apiSuccess {String} meta page meta info, e.g php.
        @apiSuccess {String} content content of data.
        """
        _query = self.get_schema()
        __query = {}
        if _query['name']:
            __query = {"name": {"$regex": _query['name']}}

        pagination = await paginate(collection=event_collection, query=__query, page=_query['page'],
                                    per_page=_query['per_page'], order_by=_query['sort'], desc=_query['desc'])
        rst = [(await Event.get_event(_id=doc['_id'])).to_dict() async for doc in pagination.items]
        pagination.count = len(rst)
        self.write_response(rst, meta={"pagination": pagination.php_meta_pagination})

    def get_schema(self):
        try:
            _data = Schema({
                SchemaOptional("page", default=1): Use(int),
                SchemaOptional("per_page", default=20): Use(int),
                SchemaOptional("sort", default=""): str,
                SchemaOptional("desc", default=True): And(Use(int), Use(bool)),
                SchemaOptional("name", default=""): str,
            }, ignore_extra_keys=True).validate(self.get_query_args())
        except SchemaError as e:
            raise self.write_parse_args_failed_response(content=str(e))
        else:
            return _data

    async def post(self):
        _query = self.post_schema()
        try:
            cls = validator_for(_query['schema'])
            cls.check_schema(_query['schema'])
        except JSONSchemaError as e:
            raise self.write_parse_args_failed_response(content=str(e))

        event = await Event.create(name=_query['name'], schema=_query['schema'])
        self.write_response(content=event.to_dict())

    def post_schema(self):
        try:
            _data = Schema({
                "name": And(str, lambda x: 0 < len(x) < 32),
                "schema": And(dict, Use(convert_json_schema_to_son)),
            }, ignore_extra_keys=True).validate(self.get_body_args())
        except SchemaError as e:
            raise self.write_parse_args_failed_response(content=str(e))
        else:
            return _data


class EventIdHandler(BaseRequestHandler, ABC):
    def get(self, event_id: str):
        pass

    def post(self, event_id: str):
        pass

    def delete(self, event_id: str):
        pass
