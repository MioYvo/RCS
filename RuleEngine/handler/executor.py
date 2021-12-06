# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/31/21 4:54 AM
import datetime
import json
from typing import Optional

from aio_pika import IncomingMessage
from bson import ObjectId
from schema import Schema, SchemaError, Use

from model.odm import Record, Rule, Result, ResultInRecordStatus, \
    suggest_final_punishment
from utils.fastapi_app import app
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
        else:
            record: Record = await app.state.engine.get_by_id(Record, data['record'])
            rule: Rule = await app.state.engine.get_by_id(Rule, data['rule'])
            rule_schema: list = data['rule_schema']

            if not (rule and record):
                return await self.ack(message)

        # self.logger.info(trigger_by=record.id, event=record.event.name, rule_name=rule.name)
        try:
            if RuleParser.evaluate_rule(rule_schema):
                # rule matched
                self.logger.info('✓RuleMatched✓', rule_id=rule.id, rule_name=rule.name)
                result = Result(rule=rule.id, record=record.id, processed=False)
                await app.state.engine.save(result)
            else:
                # rule not matched
                self.logger.info('✗RuleNotMatch✗', rule_id=rule.id, rule_name=rule.name, rule=rule.name)
                result = None
        except Exception as e:
            self.logger.exceptions(e, where='render_rule')
            await self.reject(message, requeue=False)
        else:
            await self.update_results_in_record(record=record, rule=rule, result=result)
        finally:
            try:
                # may rejected msg before this
                await self.ack(message)
            except Exception as e:
                self.logger.debug(e, where='ack msg')

    async def update_results_in_record(self, record: Record, rule: Rule, result: Optional[Result] = None):
        """
        Update Record.results, which is rule-result mapping
        :param record:
        :param rule:
        :param result:
        :return:
        """

        inc = {
            "punish.total_punish_level": rule.punish_level, "punish.results_done": 1,
        }
        if result:
            inc["punish.hit_punish_level"] = rule.punish_level

        record = await app.state.engine.find_one_and_update(
            Record, {"_id": record.id, "results.rule_id": rule.id},
            update={
                "$set": {
                    "results.$.status": ResultInRecordStatus.HIT if result else ResultInRecordStatus.DONE,
                    "results.$.done_time": datetime.datetime.utcnow(),
                    "results.$.result_id": result.id if result else None
                },
                "$inc": inc
            }
        )
        if record:
            self.logger.info(record.id, record.punish.log_status(), total=len(record.results))
            # record = await app.state.engine.refresh(record)
            if record.punish.results_done == len(record.results):
                action = suggest_final_punishment(record.punish.hit_punish_level)
                if action:
                    record = await app.state.engine.find_one_and_update(Record, Record.id == record.id,
                                                                        {"$set": {"punish.action": action}})
                self.logger.info(f"suggest:punish", record.punish.log_status(), total=len(record.results))
        else:
            self.logger.info(f"{Record} not fund")
            # return app.state.engine.find_one(Record, Record.id == record.id)

            # self.logger.info(f"update_results", modified_count=rst.modified_count, rule=rule.id,
            #                  result=True if result else False)

    async def auto_punish(self, record: Record) -> None:
        """
        Check Record.results, make sure all rules are executed done, then punish them depends on conditions
        TODO Create a scheduled task to check time-out Rule Executor, for fall-back processing.
        :return:
        """
        if record.punish.results_done == len(record.results):
            action = suggest_final_punishment(record.punish.hit_punish_level)
            await app.state.engine.update_one(Record, Record.id == record.id, {"$set": {"punish.action": action}})
            self.logger.info(f"suggest:punish", record.punish)

        # undone_record = await app.state.engine.gets(
        #     Record, {
        #         "_id": record.id,
        #         "results.status": {
        #             "$in": [ResultInRecordStatus.WAIT.value, ResultInRecordStatus.DISPATCHED.value]
        #         }
        #     },
        # )
        # if not undone_record:
        #     # all rules' result are executed
        #     # find all auto punished rules to calculate FINAL punish level
        #     record = await app.state.engine.find_one(Record, Record.id == record.id)
        #     record_punish_level: dict = record.rules_punish_level()
        #     final_punish_action: Optional[Action] = None
        #     for _level in PUNISH_ACTION_LEVEL_MAP.keys():
        #         if record_punish_level['done'] >= _level:
        #             final_punish_action = PUNISH_ACTION_LEVEL_MAP[_level]
        #         else:
        #             break
        #     self.logger.info(f'auto_punish::{record_punish_level}::{final_punish_action}')
        #     if final_punish_action:
        #         # DO punish
        #         pass

    async def validate_message(self, message) -> Optional[dict]:
        try:
            data = json.loads(message.body)
            _data = Schema({
                "record": Use(ObjectId),
                "rule": Use(ObjectId),
                "rule_schema": list,
            }).validate(data)
        except SchemaError as e:
            self.logger.error(e)
            return None
        except Exception as e:
            self.logger.error(e)
            return None
        else:
            return _data
