from typing import Optional, Union, Tuple

import jsonschema
from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.results import UpdateResult, InsertOneResult
from pytz import utc

from config.clients import event_collection
from model import BaseCollection
from utils.logger import Logger
from utils.mbson import convert_son_to_json_schema
from utils.gtz import Dt


class Event(BaseCollection):
    collection: AgnosticCollection = event_collection
    logger = Logger('EventColl')

    def __init__(self, _id: Union[str, ObjectId], name: str = ''):
        super().__init__(_id)
        self.name: str = name
        self.schema: Optional[dict] = None

    async def load(self):
        await super(Event, self).load()
        if self.schema:
            self.schema = convert_son_to_json_schema(self.schema)

    @classmethod
    async def create(cls, name: str, schema: dict) -> "Event":
        insert_rst: InsertOneResult = await cls.collection.insert_one({
            "schema": schema, "name": name,
            "update_at": Dt.utc_now(), "create_at": Dt.utc_now()
        })
        return await cls.get_by_id(_id=str(insert_rst.inserted_id))

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
            "update_at": self.update_at,
            "create_at": self.create_at,
        }
