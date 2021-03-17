import json

from aio_pika import IncomingMessage
from bson import ObjectId
from pymongo.results import InsertOneResult
from schema import Schema, SchemaError, And, Use

from config.clients import record_collection
from config import MONGO_COLLECTION_RECORD
from utils.gtz import Dt
from utils.logger import Logger


class AccessConsumer:
    logger = Logger(name='AccessConsumer')

    def __init__(self, amqp_connection):
        self.amqp_connection = amqp_connection
        self.msg = None
        self.routing_key = "event"

    @classmethod
    async def ack(cls, msg: IncomingMessage) -> None:
        if isinstance(msg, IncomingMessage):
            try:
                await msg.ack()
            except Exception as e:
                cls.logger.error(e)

    @classmethod
    async def reject(cls, msg: IncomingMessage, requeue: bool = False) -> None:
        if isinstance(msg, IncomingMessage):
            try:
                await msg.reject(requeue=requeue)
            except Exception as e:
                cls.logger.error(e)

    def validate_message(self, message):
        try:
            data = json.loads(message.body)
            _data = Schema({
                "event_id": Use(ObjectId),
                "event_ts": And(int, Use(Dt.from_ts)),
                "event": dict,
            }).validate(data)
        except SchemaError as e:
            self.logger.error(e)
            return None
        except Exception as e:
            self.logger.error(e)
            return None
        else:
            return _data

    async def consume(self, message: IncomingMessage):
        data = self.validate_message(message=message)
        if not data:
            return await self.ack(message)

        data['create_at'] = Dt.utc_now()

        rst: InsertOneResult = await record_collection.insert_one(data)
        self.logger.info("InsertSuccess", collection=MONGO_COLLECTION_RECORD, doc=rst.inserted_id)
        doc = await record_collection.find_one(rst.inserted_id)
        self.logger.info(doc)
        await self.ack(message)
