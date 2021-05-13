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

from config import SCHEMA_TTL, CACHE_NAMESPACE
from config.clients import pickle_serializer, redis_cache_no_self


class YvoEngine(AIOEngine):
    def __init__(self, motor_client: AsyncIOMotorClient = None, database: str = "test",
                 a_redis_client: Redis = None):
        super(YvoEngine, self).__init__(motor_client, database)
        self.a_redis_client = a_redis_client

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
        logger.info(f'real:get:{model}:{queries}')
        if return_doc and result:
            return result.doc(include=return_doc_include)
        else:
            return result   # may be None

    async def delete_cache(self, instance_id: Union[str, ObjectId]):
        cur = b"0"  # set initial cursor to 0
        while cur:
            cur, keys = await self.a_redis_client.scan(cur, match=f"{CACHE_NAMESPACE}*{str(instance_id)}*")
            logger.info(f'delete_cache:keys:{keys}')
            if keys:
                await self.a_redis_client.delete(*keys)

    async def save(self, instance: ModelType) -> ModelType:
        await self.delete_cache(instance.id)
        instance = await super(YvoEngine, self).save(instance=instance)
        return instance

    async def save_all(self, instances: Sequence[ModelType]) -> List[ModelType]:
        for ai in instances:
            await self.delete_cache(ai.id)
        added_instances = await super(YvoEngine, self).save_all(instances=instances)
        return added_instances

    async def delete(self, instance: ModelType) -> None:
        await self.delete_cache(instance.id)
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
            model, model.id == doc['_id'],
            return_doc=return_doc, return_doc_include=return_doc_include
        ) async for doc in motor_cursor]
