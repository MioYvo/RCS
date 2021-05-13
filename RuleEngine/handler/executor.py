# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/31/21 4:54 AM
import json
from typing import Optional

from aio_pika import IncomingMessage
from schema import Schema, And, SchemaError

from utils.rule_operator import RuleParser
from config import RULE_EXE_ROUTING_KEY
from utils.amqp_consumer import AmqpConsumer
from utils.logger import Logger


class RuleExecutorConsumer(AmqpConsumer):
    logger = Logger(name='RuleExecutorConsumer')
    routing_key = RULE_EXE_ROUTING_KEY

    async def consume(self, message: IncomingMessage):
        """
        DataProcessor:
            Record:
                Event:
                    related_rules (fetch from db)
                    agg_data(TODO create model agg_data, generate by DataProcessor):
                        related_rules

            {
                "trigger_by": {
                    // Record
                },
                "rules": [
                    {
                        "id": "1",
                        "name": "",
                        "rule": ['or',
                          ['>', 1, 2],
                          ['and',
                           ['in_', 1, 1, 2, 3],
                           ['>', "DATA::event::60637cd71b57484ca719135e::latest_record::amount", ['int', '2']]]
                          ]
                    }
                ]
            }
        :param message:
        :return:
        """
        data = await self.validate_message(message=message)
        if not data:
            return await self.ack(message)

        self.logger.info(trigger_by=data['trigger_by'])
        for rule in data["rules"]:
            try:
                _rule_schema = await RuleParser.render_rule(rule['rule'])
            except Exception as e:
                self.logger.exceptions(e, where='render_rule')
            else:
                if RuleParser.evaluate_rule(_rule_schema):
                    # match this rule
                    self.logger.info('RuleMatched', rule_id=rule['id'], rule_name=rule['name'])
                else:
                    # NOT match
                    pass
        await self.ack(message)

    async def validate_message(self, message) -> Optional[dict]:
        try:
            data = json.loads(message.body)
            _data = Schema({
                "trigger_by": dict,
                "rules": And(list, lambda x: len(x) > 0),
            }).validate(data)
        except SchemaError as e:
            self.logger.error(e)
            return None
        except Exception as e:
            self.logger.error(e)
            return None
        else:
            return _data
