from typing import Optional, List, Union, Tuple

import jsonschema
from aiocache import cached
from bson import ObjectId
from pymongo.results import UpdateResult, InsertOneResult, DeleteResult

from config.clients import redis_cache_only_kwargs, event_collection, key_builder_only_kwargs, cache, \
    pickle_serializer, logger
from config import SCHEMA_TTL
from utils.mbson import convert_son_to_json_schema
from utils.gtz import Dt


class Event:
    def __init__(self, _id: Union[str, ObjectId], name: str = ''):
        self._id: ObjectId = ObjectId(_id)
        self.name: str = name
        self.schema: Optional[dict] = None
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
        event = await event_collection.find_one({"_id": ObjectId(self._id)})
        if not event:
            self.exists = False
            return
        else:
            self.exists = True

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
        try:
            rst = await self._save()
        except Exception as e:
            logger.exceptions(e)
            return False
        else:

            return rst

    async def _save(self) -> bool:
        if not self.schema:
            raise Exception("No event_schema exists in object")
        if self._id:
            update_rst: UpdateResult = await event_collection.update_one(
                {"_id": self._id},
                {"$set": {"schema": self.schema, "name": self.name,
                          "update_at": Dt.now_ts()}},
                # projection={"_id": False},
                upsert=False
            )
            rst = True if update_rst.modified_count else False
        else:
            insert_rst: InsertOneResult = await event_collection.insert_one({
                "schema": self.schema, "name": self.name,
                "update_at": Dt.now_ts(), "create_at": Dt.now_ts()
            })
            rst = True if insert_rst.inserted_id else False
            self._id = str(insert_rst.inserted_id)

        await self.load()  # reload from db
        await self.rebuild_cache()
        return rst

    async def refresh_cache(self) -> None:
        await cache.delete(key=self.cache_key)

    async def rebuild_cache(self) -> None:
        await cache.set(key=self.cache_key, value=self, ttl=SCHEMA_TTL)

    @property
    def cache_key(self) -> str:
        return key_builder_only_kwargs(func=self.get_event, _id=self._id)

    @classmethod
    @cached(ttl=SCHEMA_TTL, serializer=pickle_serializer, **redis_cache_only_kwargs)
    async def get_event(cls, _id: Union[str, ObjectId]) -> "Event":
        logger.info(f'real get event {_id}')
        event = cls(_id=_id)
        await event.load()
        return event

    @classmethod
    async def del_events(cls, _ids: List[str]) -> DeleteResult:
        delete_result: DeleteResult = await event_collection.delete_many({"_id": {"$in": _ids}})
        for _id in _ids:
            await cls(_id).refresh_cache()
        return delete_result

    async def delete(self) -> bool:
        delete_result: DeleteResult = await event_collection.delete_one({"_id": self._id})
        await self.refresh_cache()
        return delete_result.deleted_count == 1

    def validate(self, json: dict) -> Tuple[bool, str]:
        try:
            jsonschema.validate(schema=convert_son_to_json_schema(self.schema), instance=json)
        except Exception as e:
            return False, str(e)
        else:
            return True, ''

    def to_dict(self) -> dict:
        return {
            "id": str(self._id),
            "name": self.name,
            "schema": convert_son_to_json_schema(self.schema),
            "update_at": Dt.from_ts(self.update_at),
            "create_at": Dt.from_ts(self.create_at),
        }
