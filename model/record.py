# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/17/21 4:21 PM
from typing import Union

from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.results import InsertOneResult

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
        self.event = None
        self.event_ts = None

    @classmethod
    async def create(cls, event_id: Union[str, ObjectId], event: dict, event_ts: Union[int, float]):
        insert_rst: InsertOneResult = await cls.collection.insert_one({
            "event_id": ObjectId(event_id), "event": event,
            "event_ts": Dt.from_ts(event_ts)
        })
