import json

from aio_pika import IncomingMessage
from bson import ObjectId
from schema import Schema, SchemaError, And, Use

from model.event import Event
from model.record import Record
from utils.amqp_consumer import AmqpConsumer
from utils.event_schema import EventSchema
from utils.gtz import Dt
from utils.logger import Logger


class AccessConsumer(AmqpConsumer):
    logger = Logger(name='AccessConsumer')
    routing_key = "event"

    async def validate_message(self, message):
        try:
            data = json.loads(message.body)
            _data = Schema({
                "event_id": Use(ObjectId),
                "event_ts": And(int, lambda x: Dt.from_ts(x)),
                "event": dict,
            }).validate(data)
        except SchemaError as e:
            self.logger.error(e)
            return None
        except Exception as e:
            self.logger.error(e)
            return None
        else:
            event = await Event.get_by_id(_data['event_id'])
            _data['event'] = EventSchema.validate(event.schema, _data['event'])
            return _data

    async def consume(self, message: IncomingMessage):
        data = await self.validate_message(message=message)
        if not data:
            return await self.ack(message)

        data['create_at'] = Dt.utc_now()

        record = await Record.create(event_id=data['event_id'], event=data['event'], event_ts=data['event_ts'])

        # rst: InsertOneResult = await record_collection.insert_one(data)
        self.logger.info("InsertSuccess", collection=Record, doc=record.id)
        # doc = await record_collection.find_one(rst.inserted_id)
        # self.logger.info(record)
        await self.ack(message)
