import json
import logging

from aio_pika import IncomingMessage
from pymongo.results import InsertOneResult
from schema import Schema, SchemaError, And, Use

from DataProcessor.clients import record_collection
from DataProcessor.settings import MONGO_COLLECTION_RECORD
from utils.gtz import Dt


class AccessConsumer:
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
                logging.error(e)

    @classmethod
    async def reject(cls, msg: IncomingMessage, requeue: bool = False) -> None:
        if isinstance(msg, IncomingMessage):
            try:
                await msg.reject(requeue=requeue)
            except Exception as e:
                logging.error(e)

    def validate_message(self, message):
        try:
            data = json.loads(message.body)
            _data = Schema({
                "event_id": int,
                "event_ts": And(int, Use(Dt.from_ts)),
                "event": dict
            }).validate(data)
        except SchemaError as e:
            logging.error(e)
            return None
        except Exception as e:
            logging.error(e)
            return None
        else:
            return _data

    async def consume(self, message: IncomingMessage):
        data = self.validate_message(message=message)
        if not data:
            return await self.ack(message)

        rst: InsertOneResult = await record_collection.insert_one(data)
        logging.info(f"InsertSuccess collection:{MONGO_COLLECTION_RECORD} doc:{rst.inserted_id}")
        doc = await record_collection.find_one(rst.inserted_id)
        logging.info(doc)
        await self.ack(message)
