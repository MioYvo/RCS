# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 7:41 PM
from aioredis import Redis
from bson import ObjectId
from loguru import logger
from typing import Optional, Union, Type, Dict, Any, List, Sequence

# noinspection PyProtectedMember
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCursor
from odmantic import Model, AIOEngine
from odmantic.engine import ModelType, AIOCursor
from odmantic.query import QueryExpression
from pydantic.utils import lenient_issubclass
from pymongo import ReturnDocument
from pymongo.results import UpdateResult

from config.clients import cached_instance


class YvoEngine(AIOEngine):
    def __init__(self, motor_client: AsyncIOMotorClient = None, database: str = "test",
                 a_redis_client: Redis = None):
        super(YvoEngine, self).__init__(motor_client, database)
        self.a_redis_client = a_redis_client

    @staticmethod
    def build_cache_key(instance):
        return f"{instance.__collection__}:{getattr(instance, instance.__primary_field__)}"

    async def refresh(self, instance: ModelType):
        await self.delete_cache(instance)
        await self.get_by_id(type(instance), instance.id)

    def _find(self,
              model: Type[ModelType],
              *queries: Union[
                  QueryExpression, Dict, bool
              ],  # bool: allow using binary operators with mypy
              sort: Optional[Any] = None,
              skip: int = 0,
              limit: Optional[int] = None,
              ) -> AsyncIOMotorCursor:
        """Search for Model instances matching the query filter provided

        Args:
            model: model to perform the operation on
            queries: query filter to apply
            sort: sort expression
            skip: number of document to skip
            limit: maximum number of instance fetched

        Raises:
            DocumentParsingError: unable to parse one of the resulting documents

        Returns:
            [odmantic.engine.AIOCursor][] of the query

        <!---
        #noqa: DAR401 ValueError
        #noqa: DAR401 TypeError
        #noqa: DAR402 DocumentParsingError
        -->
        """
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
        pipeline.extend(AIOEngine._cascade_find_pipeline(model))
        # only return _id, must at end of pipeline,
        # otherwise stage args may be no effective
        pipeline.append({"$project": {model.__primary_field__: 1}})
        return collection.aggregate(pipeline)

    @staticmethod
    def get_doc_primary_key(doc, model: Type[ModelType]):
        if model.__primary_field__ == 'id':
            return doc['_id'] if isinstance(doc, dict) else getattr(doc, 'id')
        else:
            if getattr(doc, "__primary_field__", None) is not None:
                return doc[model.__primary_field__] if isinstance(doc, dict) else getattr(doc, model.__primary_field__)
            else:
                return doc['_id'] if isinstance(doc, dict) else getattr(doc, 'id')

    async def find(self, model: Type[ModelType], *args, **kwargs) -> List[ModelType]:
        motor_cursor = self._find(model, *args, **kwargs)
        return [await self.get_by_id(model, self.get_doc_primary_key(doc, model)) async for doc in motor_cursor]

    async def get_by_id(self,
                        model: Type[ModelType],
                        primary_key: Union[str, ObjectId],
                        ) -> Optional[ModelType]:
        _json = await self._get_by_id(model=model, primary_key=str(primary_key))
        if _json:
            # noinspection PyTypeChecker
            return model.parse_obj(_json)
        else:
            return None

    @cached_instance
    async def _get_by_id(
            self,
            model: Type[ModelType],
            primary_key: str,
    ) -> Optional[dict]:
        """

        :param model:
        :param primary_key:
        :return: None时不缓存
        """
        logger.info(f'real:get_info:{model.__name__}:{primary_key}')
        _primary_key = ObjectId(primary_key) if model.__primary_field__ == 'id' else primary_key
        query = AIOEngine._build_query(getattr(model, model.__primary_field__) == _primary_key)
        collection = self.get_collection(model)
        pipeline: List[Dict] = [{"$match": query}, {"$limit": 1}]
        motor_cursor = collection.aggregate(pipeline)
        results = await AIOCursor(model, motor_cursor)
        if len(results) == 0:
            return None  # 不缓存
        return results[0].dict()

    async def delete_cache(self, instance: ModelType, model: Type[ModelType] = None):
        model = model or instance.__class__
        primary_key = self.get_doc_primary_key(instance, model or instance.__class__)

        key = cached_instance.get_cache_key(
            self._get_by_id, args=[self],
            kwargs=dict(model=model, primary_key=primary_key)
        )
        # if cached_instance.cache.namespace:
        #     key = f"{cached_instance.cache.namespace}:{key}"

        await cached_instance.cache.delete(key)

    async def save(self, instance: ModelType) -> ModelType:
        """
        NOT SUPPORT reference
        :param instance:
        :return:
        """
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

    async def update_many(self, model: Type[ModelType], *queries, update: Union[List[Dict], Dict] = None) -> UpdateResult:
        motor_cursor = self._find(model, *queries)
        async for doc in motor_cursor:
            await self.delete_cache(doc, model)

        collection = self.get_collection(model)
        query = AIOEngine._build_query(*queries)
        logger.debug(f"update_many::{query}::{update}")
        return await collection.update_many(filter=query, update=update)

    async def update_one(self, model: Type[ModelType], query, update: Union[List[Dict], Dict] = None) -> UpdateResult:
        instance = await self.find_one(model, query)
        if instance:
            await self.delete_cache(instance, model)

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
                                  return_document=ReturnDocument.AFTER) -> Optional[ModelType]:
        instance = await self.find_one(model, query)
        if instance:
            await self.delete_cache(instance, model)

        collection = self.get_collection(model)
        # IMPORTANT For AWS DocumentDB updateOne cannot use queries builder
        # IMPORTANT use RAW query directly for multi queries, or kwargs style query for ONE query like Record.id == xxx
        # query = AIOEngine._build_query(*queries)
        # logger.debug(f"update_one::{query}::{update}")
        rst = await collection.find_one_and_update(filter=query, update=update, return_document=return_document)
        if rst:
            primary_key = self.get_doc_primary_key(rst, model)
            return await self.get_by_id(model, primary_key=primary_key)

    async def delete_many(self, model: Type[ModelType], *queries):
        motor_cursor = self._find(model, *queries)
        async for doc in motor_cursor:
            await self.delete_cache(doc)

        collection = self.get_collection(model)
        query = AIOEngine._build_query(*queries)
        logger.debug(f"delete_many::{query}")
        return await collection.delete_many(filter=query)
