from bson import ObjectId
from schema import Schema, SchemaError, Optional as SchemaOptional, Use, And
from tornado.web import Finish

from config import AccessExchangeName, EVENT_ROUTING_KEY
from model.event import Event
from model.record import Record
from utils.amqp_publisher import publisher
from utils.gtz import Dt
from utils.mongo_paginate import paginate
from utils.web import BaseRequestHandler


class RecordHandler(BaseRequestHandler):
    async def post(self):
        """
        @api {post} /record Create Record
        @apiName CreateRecord
        @apiGroup Record

        @apiParam {String} event_id 事件id
        @apiParam {Number} [event_ts] 事件时间戳，utc, 单位毫秒
        @apiParam {Object} event 事件内容，schema定义在event_id中

        @apiUse Response
        @apiSuccess {Object} content content of data.
        @apiSuccess {String} Content.id 记录id
        @apiSuccess {String} Content.event_id 事件id
        @apiSuccess {String} Content.event_ts 事件时间戳，utc, 单位毫秒
        @apiSuccess {Object} Content.event 事件
        """
        data = await self.schema_post()
        # noinspection PyUnresolvedReferences
        tf, rst, sent_msg = await publisher(
            conn=self.application.amqp_connection,
            message=data, exchange_name=AccessExchangeName,
            routing_key=EVENT_ROUTING_KEY, timestamp=Dt.now_ts(),
        )
        if tf:
            self.write_response(content=dict(rst))
        else:
            self.write_parse_args_failed_response(content=dict(rst))

    async def schema_post(self):
        try:
            _data = Schema({
                "event_id": Use(ObjectId),
                SchemaOptional("event_ts", default=int(Dt.now_ts() * 1000)): int,
                "event": dict    # dynamic load from db and cached
            }).validate(self.get_body_args())
            # got event
            event = await Event.get_by_id(_id=_data['event_id'])
            if not event.exists:
                raise self.write_not_found_entity_response(content=dict(id=event.id))
            # validate event
            validate_rst, validate_info = event.validate(_data['event'])
            if not validate_rst:
                raise self.write_parse_args_failed_response(message=validate_info)
        except SchemaError as e:
            raise self.write_parse_args_failed_response(str(e))
        except Finish as e:
            raise e
        except Exception as e:
            raise self.write_parse_args_failed_response(str(e))
        else:
            return _data

    async def get(self):
        """
        List records
        """
        _query = self.get_schema()
        query = {}
        if _query['name']:
            query["name"] = {"$regex": _query['name']}
        pagination = await paginate(collection=Record.collection, query=query, page=_query['page'],
                                    per_page=_query['per_page'], order_by=_query['sort'], desc=_query['desc'])
        rst = [(await Record.get_by_id(_id=doc['_id'])).to_dict() async for doc in pagination.items]
        pagination.count = len(rst)
        self.write_response(rst, meta={"pagination": pagination.php_meta_pagination})

    def get_schema(self):
        try:
            _data = Schema({
                SchemaOptional("page", default=1): Use(int),
                SchemaOptional("per_page", default=20): Use(int),
                SchemaOptional("sort", default="update_at"): str,
                SchemaOptional("desc", default=True): And(Use(int), Use(bool)),

                SchemaOptional("name", default=""): str,
            }, ignore_extra_keys=True).validate(self.get_query_args())
        except SchemaError as e:
            raise self.write_parse_args_failed_response(content=str(e))
        else:
            return _data
