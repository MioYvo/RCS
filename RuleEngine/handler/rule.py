# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/30/21 7:38 PM
import json

from pymongo.errors import DuplicateKeyError, PyMongoError
from schema import Schema, SchemaError, Or, Use, And, Optional as SchemaOptional

from model.mapping import COLL_MAPPING
from model.rule import Rule
from utils.mongo_paginate import paginate
from utils.web import BaseRequestHandler
from RuleEngine.rule_operator import RuleParser


class RuleHandler(BaseRequestHandler):
    def create_rule_schema(self):
        try:
            _data = Schema({
                "rule": And(Or(list, And(Use(json.loads), list)), lambda x: RuleParser.validate(x) is None),
                "name": And(str, lambda x: len(x) <= 50),
            }).validate(self.get_body_args())
        except SchemaError as e:
            raise self.write_parse_args_failed_response(content=str(e))
        else:
            return _data

    async def post(self):
        data = self.create_rule_schema()
        # update Event and other related data source
        _coll_info = RuleParser.coll_info(data['rule'])  # {'event': [ObjectId('60637cd71b57484ca719135e')]}
        for k, v in _coll_info.items():
            coll = COLL_MAPPING.get(k)
            if not coll:
                raise self.write_parse_args_failed_response(content=f'Collection {k} not found')
            for coll_id in v:
                document_obj = await coll.get_by_id(_id=coll_id)
                if not document_obj.exists:
                    raise self.write_parse_args_failed_response(content=f'{coll.collection.name}.{coll_id} not found')

        try:
            rule = await Rule.create(name=data['name'], rule=data['rule'])
        except DuplicateKeyError as e:
            raise self.write_duplicate_entry(content=str(e))
        except PyMongoError as e:
            raise self.write_unknown_error_response(content=str(e))
        else:
            for k, v in _coll_info.items():
                coll = COLL_MAPPING[k]
                for coll_id in v:
                    document_obj = await coll.get_by_id(_id=coll_id)
                    document_obj.rules.append(rule.id)
                    await document_obj.save()
        self.write_response(content=rule.to_dict())

    async def get(self):
        _query = self.get_schema()
        __query = {}
        if _query['name']:
            __query = {"name": {"$regex": _query['name']}}

        pagination = await paginate(collection=Rule.collection, query=__query, page=_query['page'],
                                    per_page=_query['per_page'], order_by=_query['sort'], desc=_query['desc'])
        rst = [(await Rule.get_by_id(_id=doc['_id'])).to_dict() async for doc in pagination.items]
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

    async def delete(self):
        pass


class RuleIdHandler(BaseRequestHandler):
    async def get(self, rule_id: str):
        pass

    async def put(self, rule_id: str):
        pass

    async def delete(self, rule_id: str):
        pass
