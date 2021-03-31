# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/17/21 4:21 PM
from typing import Union, Optional

from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo import DESCENDING
from pymongo.results import InsertOneResult, UpdateResult

from config.clients import record_collection
from model import BaseCollection
from utils.gtz import Dt
from utils.logger import Logger


class Record(BaseCollection):
    collection: AgnosticCollection = record_collection
    logger = Logger('RecordColl')

    def __init__(self, _id: Union[str, ObjectId]):
        super().__init__(_id)
        self.event_id = None
        self.event: Optional[dict] = None
        self.event_ts = None

    @classmethod
    async def create(cls, event_id: Union[str, ObjectId], event: dict, event_ts: Union[int, float]):
        insert_rst: InsertOneResult = await cls.collection.insert_one({
            "event_id": ObjectId(event_id), "event": event,
            "event_ts": Dt.from_ts(event_ts)
        })
        return await cls.get_by_id(_id=str(insert_rst.inserted_id))

    async def _save(self) -> bool:
        if not self.event_id:
            raise Exception("No event_id exists in object")
        if self._id:
            update_rst: UpdateResult = await self.collection.update_one(
                {"_id": self._id},
                {"$set": {"event_id": self.event_id, "event": self.event, "event_ts": self.event_ts,
                          "update_at": Dt.now_ts()}},
                # projection={"_id": False},
                upsert=False
            )
            rst = True if update_rst.modified_count else False
        else:
            insert_rst: InsertOneResult = await self.collection.insert_one({
                "event_id": self.event_id, "event": self.event, "event_ts": self.event_ts,
                "update_at": Dt.now_ts(), "create_at": Dt.now_ts()
            })
            rst = True if insert_rst.inserted_id else False
            self._id = str(insert_rst.inserted_id)

        await self.load()  # reload from db
        await self.rebuild_cache()
        return rst

    @classmethod
    async def get_latest_by_event_id(cls, event_id: Union[str, ObjectId]) -> Optional["Record"]:
        record = await cls.collection.find_one(
            filter=dict(event_id=ObjectId(event_id)),
            projection={"_id": 1},
            sort=[('create_at', DESCENDING)]
        )
        if record:
            return await cls.get_by_id(_id=record['_id'])
        else:
            return None

    def to_dict(self) -> dict:
        return {
            "id": str(self._id),
            "event_id": self.event_id,
            "event": self.event,
            "event_ts": self.event_ts,
            "update_at": self.update_at,
            "create_at": self.create_at,
        }
