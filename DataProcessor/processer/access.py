import json

from aio_pika import IncomingMessage
from bson import ObjectId
from schema import Schema, SchemaError, And, Use

from config import RCSExchangeName, RULE_EXE_ROUTING_KEY, DATA_PROCESSOR_ROUTING_KEY
from model.event import Event
from model.record import Record
from model.rule import Rule
from utils.amqp_consumer import AmqpConsumer
from utils.amqp_publisher import publisher
from utils.event_schema import EventSchema
from utils.gtz import Dt
from utils.logger import Logger


class AccessConsumer(AmqpConsumer):
    logger = Logger(name='AccessConsumer')
    routing_key = DATA_PROCESSOR_ROUTING_KEY

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
            event = await Event.get_by_id(_id=_data['event_id'])
            _data['event'] = EventSchema.validate(event.schema, _data['event'])
            return _data, event

    async def consume(self, message: IncomingMessage):
        data, event = await self.validate_message(message=message)
        if not data:
            return await self.ack(message)

        data['create_at'] = Dt.utc_now()

        record = await Record.create(event_id=data['event_id'], event=data['event'], event_ts=data['event_ts'])

        # rst: InsertOneResult = await record_collection.insert_one(data)
        self.logger.info("InsertSuccess", collection=Record, doc=record.id)
        # doc = await record_collection.find_one(rst.inserted_id)
        # self.logger.info(record)
        await self.ack(message)

        await self.dispatch_to_rule_executor(record, event)

    async def dispatch_to_rule_executor(self, record: Record, event: Event):
        """
        {
            "trigger_by": {
                "id": "mio"
            },
            "rules": [
                {
                    "schema": [
                        "or",
                        [
                            ">",
                            1,
                            2
                        ],
                        [
                            "and",
                            [
                                "in_",
                                1,
                                1,
                                "DATA::event::6063d91389944d50ed73a11c::latest_record::user_id",
                                3
                            ],
                            [
                                ">",
                                "DATA::event::6063d91389944d50ed73a11c::latest_record::amount",
                                [
                                    "int",
                                    "2"
                                ]
                            ]
                        ]
                    ],
                    "id": 1,
                    "name": "test"
                }
            ]
        }
        :param record:
        :param event:
        :return:
        """
        data = {
            "trigger_by": record.to_dict(),
            "rules": [(await Rule.get_by_id(_id=rule)).to_dict() for rule in event.rules]
        }
        tf, rst, sent_msg = await publisher(
            conn=self.amqp_connection,
            message=data, exchange_name=RCSExchangeName,
            routing_key=RULE_EXE_ROUTING_KEY, timestamp=Dt.now_ts(),
        )
        if tf:
            self.logger.info('publishSuccess', routing_key=RULE_EXE_ROUTING_KEY)
        else:
            self.logger.error('publishFailed', routing_key=RULE_EXE_ROUTING_KEY)
