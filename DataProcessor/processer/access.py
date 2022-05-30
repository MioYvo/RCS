import datetime
from copy import deepcopy
from typing import Optional, Set

import loguru
from aio_pika import IncomingMessage
from odmantic import ObjectId
from pymongo.errors import DuplicateKeyError
from pymongo.results import UpdateResult
from schema import SchemaError

from config import RCSExchangeName, RULE_EXE_ROUTING_KEY, DATA_PROCESSOR_ROUTING_KEY
from model.odm import Event, Record, Rule, Status, ResultInRecord
from utils.amqp_consumer import AmqpConsumer
from utils.amqp_publisher import publisher
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
            event = await record.event_()
            event.validate_schema(record.event_data)
        except SchemaError as e:
            self.logger.exceptions(e)
            return None
        except Exception as e:
            self.logger.exceptions(e)
            return None
        else:
            return record

    async def consume(self, message: IncomingMessage):
        record = await self.validate_message(message=message)
        if not record:
            return await self.ack(message)

        try:
            record = await app.state.engine.save(record)
        except DuplicateKeyError as e:
            self.logger.info("InsertFailedDuplicateKey", collection=Record.__name__, e=e.details)
            await self.ack(message)
        except Exception as e:
            self.logger.info("InsertFailedUnknown", collection=Record.__name__, e=e)
            await self.ack(message)
        else:
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
                            True,
                            False
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
        rules: Set[ObjectId] = await record.rules()
        # if len(rules) != len(rules):
        #     await self.update_rules(rules, event=record.event)
        _rules = await app.state.engine.find(
            Rule,
            Rule.id.in_(list(rules)),
            Rule.status == Status.ON,
            {"project": {"$elemMatch": {"$eq": record.user.project}}}
        )
        self.logger.info(f'no such effective rules: {rules - {_r.id for _r in _rules}}')

        record.results = [ResultInRecord(rule_id=_rule.id, punish_level=_rule.punish_level) for _rule in _rules]
        await app.state.engine.save(record)

        for _rule in _rules:
            _rule: Rule
            _rule_name = _rule.name
            _rule_id = _rule.id
            _record_id = record.id

            _rule_schema = await RuleParser.render_rule(deepcopy(_rule.rule), record)
            if not isinstance(_rule_schema, list):
                _rule_schema = [_rule_schema]

            loguru.logger.info(f"{_rule_schema=}")

            data = {
                "record": _record_id,
                "rule": _rule_id,
                "rule_schema": _rule_schema
            }
            await self.update_results(record_id=_record_id, rule_id=_rule_id)
            tf, rst, sent_msg = await publisher(
                conn=self.amqp_connection,
                message=data, exchange_name=RCSExchangeName,
                routing_key=RULE_EXE_ROUTING_KEY, timestamp=Dt.now_ts(),
            )
            if tf:
                self.logger.info('publishSuccess', routing_key=RULE_EXE_ROUTING_KEY, rule=_rule_name, record=_record_id)
            else:
                self.logger.error('publishFailed', routing_key=RULE_EXE_ROUTING_KEY, rule=_rule_name, record=_record_id)

    async def update_results(self, record_id: ObjectId, rule_id: ObjectId):
        rst: UpdateResult = await app.state.engine.update_one(
            Record,
            {"_id": record_id, "results.rule_id": rule_id},
            update={"$set": {
                "results.$.dispatch_time": datetime.datetime.utcnow()
            }}
        )

    @staticmethod
    async def update_rules(rules, event: Event):
        event.rules = list(rules)
        await app.state.engine.save(event)
