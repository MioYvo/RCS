from typing import Optional, Union, Tuple, Dict, List

from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.results import UpdateResult, InsertOneResult

from config.clients import event_collection
from model import BaseCollection
from utils.event_schema import EventSchema
from utils.logger import Logger
from utils.mbson import convert_son_to_json_schema
from utils.gtz import Dt


class Event(BaseCollection):
    collection: AgnosticCollection = event_collection
    logger = Logger('EventColl')

    def __init__(self, _id: Union[str, ObjectId], name: str = '', rules: List[ObjectId] = None):
        super().__init__(_id)
        if rules is None:
            rules = []
        self.name: str = name
        self.schema: Optional[dict] = None

        self.rules = rules

    async def load(self):
        await super(Event, self).load()
        if self.schema:
            self.schema = convert_son_to_json_schema(self.schema)

    @classmethod
    async def create(cls, name: str, schema: dict, rules: List[Union[str, ObjectId]] = None) -> "Event":
        if rules is None:
            rules = []
        insert_rst: InsertOneResult = await cls.collection.insert_one({
            "schema": schema, "name": name, "rules": [ObjectId(rule) for rule in rules],
            "update_at": Dt.utc_now(), "create_at": Dt.utc_now()
        })
        return await cls.get_by_id(_id=str(insert_rst.inserted_id))

    async def _save(self) -> bool:
        if not self.schema:
            raise Exception("No event_schema exists in object")
        if self._id:
            update_rst: UpdateResult = await self.collection.update_one(
                {"_id": self._id},
                {"$set": {"schema": self.schema, "name": self.name, "rules": self.rules,
                          "update_at": Dt.now_ts()}},
                # projection={"_id": False},
                upsert=False
            )
            rst = True if update_rst.modified_count else False
        else:
            insert_rst: InsertOneResult = await self.collection.insert_one({
                "schema": self.schema, "name": self.name, "rules": self.rules,
                "update_at": Dt.now_ts(), "create_at": Dt.now_ts()
            })
            rst = True if insert_rst.inserted_id else False
            self._id = str(insert_rst.inserted_id)

        await self.load()  # reload from db
        await self.rebuild_cache()
        return rst

    def validate(self, json: dict) -> Tuple[bool, str]:
        try:
            EventSchema.validate(self.schema, json)
        except Exception as e:
            return False, str(e)
        else:
            return True, ''

    async def fetch_strategy_latest_record(self, metric: str):
        from model.record import Record
        record = await Record.get_latest_by_event_id(event_id=self.id)
        if not record:
            raise Exception('record not found')
        if record.event.get(metric) is not None:
            return record.event[metric]
        else:
            raise Exception('metric func not implemented')

    def to_dict(self) -> dict:
        return {
            "id": str(self._id),
            "name": self.name,
            "schema": self.schema,
            "rules": self.rules,
            "update_at": self.update_at,
            "create_at": self.create_at,
        }
