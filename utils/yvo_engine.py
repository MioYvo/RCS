# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 7:41 PM
from aioredis import Redis
from loguru import logger
from typing import Optional, Union, Type, Dict, Any, List, Sequence

from aiocache import cached
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import Model, AIOEngine, ObjectId
from odmantic.engine import ModelType
from odmantic.query import QueryExpression
from pydantic.utils import lenient_issubclass
from pymongo import ReturnDocument
from pymongo.results import UpdateResult

from config import SCHEMA_TTL, CACHE_NAMESPACE
from config.clients import pickle_serializer, redis_cache_no_self


class YvoEngine(AIOEngine):
    def __init__(self, motor_client: AsyncIOMotorClient = None, database: str = "test",
                 a_redis_client: Redis = None):
        super(YvoEngine, self).__init__(motor_client, database)
        self.a_redis_client = a_redis_client

    @staticmethod
    def build_cache_key(instance):
        return f"{instance.__collection__}:{getattr(instance, instance.__primary_field__)}"

    async def refresh(self, instance: ModelType):
        await self.find_one(type(instance), type(instance).id == instance.id)

    # TODO to make cache without pickle problems, may inherit AIOEngine.find and AIOCursor
    # @cached(ttl=SCHEMA_TTL, serializer=pickle_serializer, **redis_cache_no_self)
    async def find_one(
        self,
        model: Type[ModelType],
        *queries: Union[
            QueryExpression, Dict, bool
        ],  # bool: allow using binary operators w/o plugin,
        sort: Optional[Any] = None,
        return_doc: bool = False,
        return_doc_include: Optional[set] = None,
    ) -> Union[Optional[ModelType], Optional[Dict]]:
        result = await super(YvoEngine, self).find_one(model, *queries, sort=sort)
        logger.debug(f'real:get:{model}:{queries}')
        if return_doc and result:
            return result.doc(include=return_doc_include)
        else:
            return result   # may be None

    async def delete_cache(self, instance: ModelType):
        key = self.build_cache_key(instance)
        cur = b"0"  # set initial cursor to 0
        while cur:
            cur, keys = await self.a_redis_client.scan(cur, match=f"{CACHE_NAMESPACE}*{str(key)}*")
            logger.debug(f'delete_cache:keys:{keys}')
            if keys:
                await self.a_redis_client.delete(*keys)

    async def save(self, instance: ModelType) -> ModelType:
        await self.delete_cache(instance)
        instance = await super(YvoEngine, self).save(instance=instance)
        return instance

    async def save_all(self, instances: Sequence[ModelType]) -> List[ModelType]:
        for ai in instances:
            await self.delete_cache(ai)
        added_instances = await super(YvoEngine, self).save_all(instances=instances)
        return added_instances

    async def delete(self, instance: ModelType) -> None:
        await self.delete_cache(instance)
        await super(YvoEngine, self).delete(instance=instance)

    async def gets(self,
                   model: Type[ModelType],
                   *queries: Union[QueryExpression, Dict, bool],
                   sort: Optional[Any] = None,
                   skip: int = 0,
                   limit: Optional[int] = None,
                   return_doc: bool = False,

                   return_doc_include: Optional[set] = None) -> List[Model]:

        if not lenient_issubclass(model, Model):
            raise TypeError("Can only call find with a Model class")
        sort_expression = self._validate_sort_argument(sort)
        if limit is not None and limit <= 0:
            raise ValueError("limit has to be a strict positive value or None")
        if skip < 0:
            raise ValueError("skip has to be a positive integer")
        query = AIOEngine._build_query(*queries)
        collection = self.get_collection(model)
        pipeline: List[Dict] = [{"$match": query}]
        if sort_expression is not None:
            pipeline.append({"$sort": sort_expression})
        if skip > 0:
            pipeline.append({"$skip": skip})
        if limit is not None and limit > 0:
            pipeline.append({"$limit": limit})
        # Only retrieve _id from db, use find_one to hit cache
        pipeline.append({"$project": {"_id": 1}})
        pipeline.extend(AIOEngine._cascade_find_pipeline(model))
        motor_cursor = collection.aggregate(pipeline)
        return [await self.find_one(
            model, getattr(model, model.__primary_field__) == doc['_id'],
            return_doc=return_doc, return_doc_include=return_doc_include
        ) async for doc in motor_cursor]

    async def yvo_pipeline(self, model: Type[ModelType], *queries, pipeline: List[Dict] = None) -> List[Dict]:
        if not pipeline:
            pipeline = []
        if queries:
            query = AIOEngine._build_query(*queries)
            _pipeline: List[Dict] = [{"$match": query}]
            _pipeline.extend(pipeline)
        else:
            _pipeline = pipeline
        # logger.info(f"pipeline::{_pipeline}")
        collection = self.get_collection(model)
        motor_cursor = collection.aggregate(_pipeline)
        return [doc async for doc in motor_cursor]

    async def update_many(self, model: Type[ModelType], *queries, update: List[Dict] = None) -> UpdateResult:
        collection = self.get_collection(model)
        query = AIOEngine._build_query(*queries)
        logger.debug(f"update_many::{query}::{update}")
        return await collection.update_many(filter=query, update=update)

    async def count(self, model: Type[ModelType], *queries):
        if not lenient_issubclass(model, Model):
            raise TypeError("Can only call count with a Model class")
        query = AIOEngine._build_query(*queries)
        collection = self.database[model.__collection__]
        logger.info(f"update_many::{query}")
        count = await collection.count_documents(query)
        return int(count)

    async def update_one(self, model: Type[ModelType], query, update: List[Dict] = None) -> UpdateResult:
        collection = self.get_collection(model)
        # IMPORTANT For AWS DocumentDB updateOne cannot use queries builder
        # IMPORTANT use RAW query directly for multi queries, or kwargs style query for ONE query like Record.id == xxx
        # query = AIOEngine._build_query(*queries)
        # logger.debug(f"update_one::{query}::{update}")
        return await collection.update_one(filter=query, update=update)

    async def find_one_and_update(self,
                                  model: Type[ModelType],
                                  query,
                                  update: List[Dict] = None,
                                  return_document=ReturnDocument.AFTER) -> dict:
        collection = self.get_collection(model)
        # IMPORTANT For AWS DocumentDB updateOne cannot use queries builder
        # IMPORTANT use RAW query directly for multi queries, or kwargs style query for ONE query like Record.id == xxx
        # query = AIOEngine._build_query(*queries)
        # logger.debug(f"update_one::{query}::{update}")
        return await collection.find_one_and_update(filter=query, update=update, return_document=return_document)

    async def delete_many(self, model: Type[ModelType], *queries):
        collection = self.get_collection(model)
        query = AIOEngine._build_query(*queries)
        logger.debug(f"delete_many::{query}")
        return await collection.delete_many(filter=query)
