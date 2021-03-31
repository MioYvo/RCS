from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.results import DeleteResult
from schema import Schema, SchemaError, Optional as SchemaOptional, Use, And

from config.clients import event_collection
from model.event import Event
from model.rule import Rule
from utils.event_schema import EventSchema
from utils.mongo_paginate import paginate
from utils.web import BaseRequestHandler


class EventHandlerBase(BaseRequestHandler):
    async def post_schema(self):
        try:
            origin_data = self.get_body_args()
            _data = Schema({
                "name": And(str, lambda x: 0 < len(x) < 32),
                "schema": And(dict, Use(EventSchema.parse)),
                SchemaOptional("rules", default=[]): And(Use(set), {Use(ObjectId)}, Use(list)),
            }, ignore_extra_keys=True).validate(origin_data)
        except SchemaError as e:
            raise self.write_parse_args_failed_response(content=str(e))
        else:
            for rule_id in _data['rules']:
                docu = await Rule.get_by_id(rule_id)
                if not docu.exists:
                    raise self.write_parse_args_failed_response(content=f'Rule({rule_id}) not found')
            return _data, origin_data['schema']


class EventHandler(EventHandlerBase):
    async def get(self):
        """
        @api {get} /event List Events
        @apiName ListEvents
        @apiGroup Event

        @apiParam {String="name", "create_at", "update_at", "_id"} [sort="update_at"] 排序键名
        @apiParam {String="0", "1"} [desc="1"] 是否倒序
        @apiParam {String} [name=""] 搜索事件名字

        @apiUse Response
        @apiSuccess {Object} meta.pagination 分页信息
        @apiSuccess {Number} meta.pagination.total 总数量
        @apiSuccess {Number} meta.pagination.count 当前页数量
        @apiSuccess {Number} meta.pagination.per_page 每页数量
        @apiSuccess {Number} meta.pagination.current_page 当前页码
        @apiSuccess {Number} meta.pagination.total_pages 总页码
        @apiSuccess {Object} meta.pagination.links 链接

        @apiSuccess {Object[]} content List of data content.
        @apiSuccess {String} content.id 事件id
        @apiSuccess {String} content.name 事件名
        @apiSuccess {Object} content.schema 事件schema，JSON Schema draft#7
        @apiSuccess {String} content.update_at 修改时间, UTC
        @apiSuccess {String} content.create_at 创建时间, UTC
        """
        _query = self.get_schema()
        __query = {}
        if _query['name']:
            __query = {"name": {"$regex": _query['name']}}

        pagination = await paginate(collection=event_collection, query=__query, page=_query['page'],
                                    per_page=_query['per_page'], order_by=_query['sort'], desc=_query['desc'])
        rst = [(await Event.get_by_id(_id=doc['_id'])).to_dict() async for doc in pagination.items]
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

    async def post(self):
        """
        @api {post} /event Create Event
        @apiName CreateEvent
        @apiGroup Event

        @apiParam {String} name 事件名字
        @apiParam {Object} schema JSON Schema draft#7 4 3

        @apiUse Response
        @apiSuccess {Object} content content of data.
        @apiSuccess {String} Content.id 事件id
        @apiSuccess {String} Content.name 事件名
        @apiSuccess {Object} Content.schema 事件schema，JSON Schema draft#7
        @apiSuccess {String} Content.update_at 修改时间, UTC
        @apiSuccess {String} Content.create_at 创建时间, UTC
        """
        _query, origin_schema = await self.post_schema()
        try:
            event = await Event.create(name=_query['name'], schema=origin_schema, rules=_query['rules'])
        except DuplicateKeyError as e:
            raise self.write_duplicate_entry(content=str(e))
        except PyMongoError as e:
            raise self.write_unknown_error_response(content=str(e))
        self.write_response(content=event.to_dict())

    async def delete(self):
        """
        @api {delete} /event Delete Events
        @apiName DeleteEvents
        @apiGroup Event

        @apiParam {BodyParam_String[]} ids 事件id列表

        @apiUse Response
        @apiSuccess {Object} content content of data.
        @apiSuccess {Number} Content.deleted_count 已删除数量
        """
        delete_result: DeleteResult = await Event.delete_many(self.delete_schema()['ids'])
        self.write_response(content=dict(deleted_count=delete_result.deleted_count))

    def delete_schema(self):
        try:
            _data = Schema({
                "ids": [And(str, Use(ObjectId))]
            }).validate(self.get_body_args())
        except SchemaError as e:
            raise self.write_parse_args_failed_response(content=str(e))
        else:
            return _data


class EventIdHandler(EventHandlerBase):
    def schema_event_id(self, event_id) -> ObjectId:
        try:
            return ObjectId(event_id)
        except (InvalidId, TypeError) as e:
            raise self.write_parse_args_failed_response(content=str(e))

    async def get(self, event_id: str):
        """
        @api {get} /event/:event_id Get Event Detail
        @apiName GetEventDetail
        @apiGroup Event

        @apiParam {PathParam_String} event_id 事件id

        @apiUse Response
        @apiSuccess {Object[]} content List of data content.
        @apiSuccess {String} content.id 事件id
        @apiSuccess {String} content.name 事件名
        @apiSuccess {Object} content.schema 事件schema，JSON Schema draft#7
        @apiSuccess {String} content.update_at 修改时间, UTC
        @apiSuccess {String} content.create_at 创建时间, UTC
        """
        event_id: ObjectId = self.schema_event_id(event_id)
        event = await Event.get_by_id(_id=event_id)
        if not event.exists:
            raise self.write_not_found_entity_response()
        self.write_response(content=event.to_dict())

    async def put(self, event_id: str):
        """
        @api {post} /event/:event_id Modify Event
        @apiName ModifyEvent
        @apiGroup Event

        @apiParam {PathParam_String} event_id 事件id
        @apiParam {BodyParam_String} name 事件名字
        @apiParam {BodyParam_Object} schema JSON Schema draft#7

        @apiUse Response
        @apiSuccess {Object} content content of data.
        @apiSuccess {String} Content.id 事件id
        @apiSuccess {String} Content.name 事件名
        @apiSuccess {Object} Content.schema 事件schema，JSON Schema draft#7
        @apiSuccess {String} Content.update_at 修改时间, UTC
        @apiSuccess {String} Content.create_at 创建时间, UTC
        """
        event_id: ObjectId = self.schema_event_id(event_id)
        event = await Event.get_by_id(_id=event_id)
        if not event.exists:
            raise self.write_not_found_entity_response()

        _query, origin_schema = self.post_schema()
        event.schema = origin_schema
        event.name = _query['name']
        await event.save()
        self.write_response(content=event.to_dict())

    async def delete(self, event_id: str):
        """
        @api {delete} /event/:event_id Delete Event
        @apiName DeleteEvent
        @apiGroup Event

        @apiParam {PathParam_String} event_id 事件id

        @apiUse Response
        @apiSuccess {Object} content content of data.
        @apiSuccess {String} Content.id 事件id
        @apiSuccess {String} Content.name 事件名
        @apiSuccess {Object} Content.schema 事件schema，JSON Schema draft#7
        @apiSuccess {String} Content.update_at 修改时间, UTC
        @apiSuccess {String} Content.create_at 创建时间, UTC
        """
        event_id: ObjectId = self.schema_event_id(event_id)
        event = await Event.get_by_id(_id=event_id)
        if not event.exists:
            raise self.write_not_found_entity_response()

        if await event.delete():
            self.write_no_content_response()
        else:
            self.write_logic_error_response(content=dict(id=event_id))
