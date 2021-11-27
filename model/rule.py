# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/30/21 7:27 PM
from typing import Union

from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.results import InsertOneResult, UpdateResult

from config.clients import rule_collection
from model import BaseCollection
from utils.gtz import Dt
from utils.logger import Logger


class Rule(BaseCollection):
    collection: AgnosticCollection = rule_collection
    logger = Logger('RuleColl')

    def __init__(self, _id: Union[str, ObjectId], name: str = '', rule=None):
        super(Rule, self).__init__(_id=_id)
        if rule is None:
            rule = []
        self.name = name
        self.rule = rule

    @classmethod
    async def create(cls, name: str, rule: list) -> "Rule":
        insert_rst: InsertOneResult = await cls.collection.insert_one({
            "rule": rule, "name": name,
            "update_at": Dt.utc_now(), "create_at": Dt.utc_now()
        })
        return await cls.get_by_id(_id=str(insert_rst.inserted_id))

    def to_dict(self) -> dict:
        return {
            "id": str(self._id),
            "name": self.name,
            "rule": self.rule,
            "update_at": self.update_at,
            "create_at": self.create_at,
        }

    async def _save(self) -> bool:
        if not self.rule:
            raise Exception("No event_schema exists in object")
        if self._id:
            update_rst: UpdateResult = await self.collection.update_one(
                {"_id": self._id},
                {"$set": {"rule": self.rule, "name": self.name,
                          "update_at": Dt.now_ts()}},
                # projection={"_id": False},
                upsert=False
            )
            rst = True if update_rst.modified_count else False
        else:
            insert_rst: InsertOneResult = await self.collection.insert_one({
                "rule": self.rule, "name": self.name,
                "update_at": Dt.now_ts(), "create_at": Dt.now_ts()
            })
            rst = True if insert_rst.inserted_id else False
            self._id = str(insert_rst.inserted_id)

        await self.load()  # reload from db
        await self.rebuild_cache()
        return rst
