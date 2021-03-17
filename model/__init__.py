from typing import List, Union

from aiocache import cached
from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.results import DeleteResult

from config.clients import redis_cache_only_kwargs, key_builder_only_kwargs, cache, pickle_serializer, logger
from config import SCHEMA_TTL
from utils.logger import Logger


class BaseCollection:
    collection: AgnosticCollection = None
    logger: Logger = Logger(name='BaseCollection')

    def __init__(self, _id: Union[str, ObjectId]):
        self._id: ObjectId = ObjectId(_id)
        self.create_at = None
        self.update_at = None
        self.exists = False

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = ObjectId(value)

    async def load(self):
        event = await self.collection.find_one({"_id": ObjectId(self._id)})
        if not event:
            self.exists = False
            return
        else:
            self.exists = True

        for attr in event:
            if hasattr(self, attr):
                setattr(self, attr, event[attr])

    @classmethod
    async def create(cls):
        raise NotImplementedError

    async def save(self) -> bool:
        try:
            rst = await self._save()
        except Exception as e:
            logger.exceptions(e)
            return False
        else:

            return rst

    async def _save(self) -> bool:
        raise NotImplementedError
        # if not self.schema:
        #     raise Exception("No event_schema exists in object")
        # if self._id:
        #     update_rst: UpdateResult = await event_collection.update_one(
        #         {"_id": self._id},
        #         {"$set": {"schema": self.schema, "name": self.name,
        #                   "update_at": Dt.now_ts()}},
        #         # projection={"_id": False},
        #         upsert=False
        #     )
        #     rst = True if update_rst.modified_count else False
        # else:
        #     insert_rst: InsertOneResult = await event_collection.insert_one({
        #         "schema": self.schema, "name": self.name,
        #         "update_at": Dt.now_ts(), "create_at": Dt.now_ts()
        #     })
        #     rst = True if insert_rst.inserted_id else False
        #     self._id = str(insert_rst.inserted_id)
        #
        # await self.load()  # reload from db
        # await self.rebuild_cache()
        # return rst

    async def refresh_cache(self) -> None:
        await cache.delete(key=self.cache_key)

    async def rebuild_cache(self) -> None:
        await cache.set(key=self.cache_key, value=self, ttl=SCHEMA_TTL)

    @property
    def cache_key(self) -> str:
        return key_builder_only_kwargs(func=self.get_by_id, _id=self._id)

    @classmethod
    @cached(ttl=SCHEMA_TTL, serializer=pickle_serializer, **redis_cache_only_kwargs)
    async def get_by_id(cls, _id: Union[str, ObjectId]):
        event = cls(_id=_id)
        logger.info(f'real get {event.collection} {_id}')
        await event.load()
        return event

    @classmethod
    async def del_events(cls, _ids: List[str]) -> DeleteResult:
        delete_result: DeleteResult = await cls.collection.delete_many({"_id": {"$in": _ids}})
        for _id in _ids:
            await cls(_id).refresh_cache()
        return delete_result

    async def delete(self) -> bool:
        delete_result: DeleteResult = await self.collection.delete_one({"_id": self._id})
        await self.refresh_cache()
        return delete_result.deleted_count == 1

    def to_dict(self) -> dict:
        raise NotImplementedError
