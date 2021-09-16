from copy import deepcopy
from typing import Optional

from aio_pika import IncomingMessage
from loguru import logger
from schema import SchemaError

from config import RCSExchangeName, RULE_EXE_ROUTING_KEY, DATA_PROCESSOR_ROUTING_KEY
from model.odm import Event, Record, Rule, Status
from utils.amqp_consumer import AmqpConsumer
from utils.amqp_publisher import publisher
from utils.event_schema import EventSchema
from utils.gtz import Dt
from utils.logger import Logger
from utils.fastapi_app import app
from utils.rule_operator import RuleParser


class AccessConsumer(AmqpConsumer):
    logger = Logger(name='AccessConsumer')
    routing_key = DATA_PROCESSOR_ROUTING_KEY

    async def validate_message(self, message) -> Optional[Record]:
        try:
            record: Record = Record.parse_raw(message.body)
            record.event_data = EventSchema.validate(record.event.rcs_schema, record.event_data)
        except SchemaError as e:
            self.logger.error(e)
            return None
        except Exception as e:
            self.logger.error(e)
            return None
        else:
            return record

    async def consume(self, message: IncomingMessage):
        record = await self.validate_message(message=message)
        if not record:
            return await self.ack(message)

        record = await app.state.engine.save(record)

        # rst: InsertOneResult = await record_collection.insert_one(data)
        self.logger.info("InsertSuccess", collection=Record, doc=record.id)
        # doc = await record_collection.find_one(rst.inserted_id)
        # self.logger.info(record)
        await self.ack(message)

        await self.dispatch_to_rule_executor(record)

    async def dispatch_to_rule_executor(self, record: Record):
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
        :return:
        """
        rules = await record.rules()
        # if len(rules) != len(rules):
        #     await self.update_rules(rules, event=record.event)
        for _rule in rules:
            _rule: Rule
            # may Replace rule's schema with record data here
            # rule = await app.state.engine.find_one(Rule, Rule.id == rule, Rule.status == Status.ON, Rule.project)
            rule = await app.state.engine.find_one(
                Rule,
                {
                    "_id": {"$eq": _rule},
                    "status": {"$eq": Status.ON},
                    "project": {"$elemMatch": {"$eq": record.user.project}}
                }
            )
            if not rule:
                self.logger.info(f'no such rule effective: {_rule}')
                continue
            # record.reformat_event_data()
            rule_schema = deepcopy(rule.rule)
            _rule_schema = await RuleParser.render_rule(rule_schema, record)
            if not isinstance(_rule_schema, list):
                _rule_schema = [_rule_schema]

            data = {
                "record": record.id,
                "rule": rule.id,
                "rule_schema": _rule_schema
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

    async def update_rules(self, rules, event: Event):
        event.rules = list(rules)
        await app.state.engine.save(event)
