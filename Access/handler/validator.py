from typing import Optional

from aiocache import cached
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.results import UpdateResult, InsertOneResult

from Access.clients import redis_cache_only_kwargs, event_collection, key_builder_only_kwargs, cache, \
    pickle_serializer, logger
from Access.settings import SCHEMA_TTL
from utils.mbson import convert_son_to_json_schema
from utils.gtz import Dt


class Event:
    def __init__(self, _id: str, name: str = ''):
        self._id: str = _id
        self.name: str = name
        self.schema: Optional[dict] = None
        self.create_at = None
        self.update_at = None

    async def load(self):
        event = await event_collection.find_one({"_id": ObjectId(self._id)})
        if not event:
            return
        for attr in event:
            if hasattr(self, attr):
                setattr(self, attr, event[attr])
        if self.schema:
            self.schema = convert_son_to_json_schema(self.schema)

    @classmethod
    async def create(cls, name: str, schema: dict) -> "Event":
        insert_rst: InsertOneResult = await event_collection.insert_one({
            "schema": schema, "name": name,
            "update_at": Dt.now_ts(), "create_at": Dt.now_ts()
        })
        return await cls.get_event(_id=str(insert_rst.inserted_id))

    async def save(self) -> bool:
        if not self.schema:
            raise Exception("No event_schema exists in object")
        if self._id:
            update_rst: UpdateResult = await event_collection.update_one(
                {"_id": self._id},
                {"$set": {"schema": self.schema, "name": self.name,
                          "update_at": Dt.now_ts()}},
                # projection={"_id": False},
                upsert=False,
                return_document=ReturnDocument.AFTER
            )
            rst = True if update_rst.modified_count else False
        else:
            insert_rst: InsertOneResult = await event_collection.insert_one({
                "schema": self.schema, "name": self.name,
                "update_at": Dt.now_ts(), "create_at": Dt.now_ts()
            })
            rst = True if insert_rst.inserted_id else False
            self._id = str(insert_rst.inserted_id)

        self.refresh_cache()
        return rst

    def refresh_cache(self):
        cache.delete(key=self.get_event_cache_k)

    @property
    def get_event_cache_k(self):
        return key_builder_only_kwargs(func=self.get_event, _id=self._id)

    @classmethod
    @cached(ttl=SCHEMA_TTL, serializer=pickle_serializer, **redis_cache_only_kwargs)
    async def get_event(cls, _id: str) -> "Event":
        logger.info(f'real get event {_id}')
        event = cls(_id=_id)
        await event.load()
        return event

    def to_dict(self):
        return {
            "id": str(self._id),
            "name": self.name,
            "schema": convert_son_to_json_schema(self.schema),
            "update_at": Dt.from_ts(self.update_at),
            "create_at": Dt.from_ts(self.create_at),
        }
