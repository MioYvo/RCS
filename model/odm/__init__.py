# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 6:27 PM
import datetime
from decimal import Decimal
from enum import Enum
from functools import reduce
from typing import List, Optional, Union, Set, Dict

from bson import Decimal128
from loguru import logger
from odmantic.bson import BSON_TYPES_ENCODERS
from pydantic import validator, root_validator
from pymongo import IndexModel
from odmantic import Model, ObjectId, Reference, Field, EmbeddedModel

from utils.exceptions import RCSExcErrArg
from utils.event_schema import EventSchema
from utils.gtz import Dt
    

class RuleExecuteType(str, Enum):
    manual = 'manual'
    automatic = "automatic"


class RulePunishLevel(int, Enum):
    level_1 = 1
    level_5 = 5
    level_10 = 10
    level_20 = 20
    level_30 = 30
    level_50 = 50


class ResultInRecordStatus(str, Enum):
    WAIT = "wait"
    DISPATCHED = "dispatched"
    DONE = "done"
    HIT = "hit"


class Status(str, Enum):
    ON = "on"
    OFF = "off"


class PredefinedEventName(str, Enum):
    withdraw = "withdraw"
    recharge = "recharge"


class Action(str, Enum):
    NOTHING = "NOTHING"
    WARNING = "WARNING"
    REFUSE_OPERATION = "REFUSE_OPERATION"
    BLOCK_USER = 'BLOCK_USER'
    BAN_USER_LOGIN = "BAN_USER_LOGIN"
    BAN_USER_WITHDRAW = "BAN_USER_LOGIN"


class HandlerRole(str, Enum):
    ADMIN = "admin"
    CUSTOMER_SERVICE = "customer_service"  # 客服


# if FINAL punish level >= MAP(key), then punish action aka. MAP(value)
# higher level harder punishment
PUNISH_ACTION_LEVEL_MAP = {
    1: Action.WARNING,
    5: Action.REFUSE_OPERATION,
    10: Action.BAN_USER_WITHDRAW,
    15: Action.BAN_USER_LOGIN,
    50: Action.BLOCK_USER
}


def suggest_final_punishment(done_punish_level: int) -> str:
    final_punish_action = ""
    for _level in PUNISH_ACTION_LEVEL_MAP.keys():   # Python3.7: Guarantee ordered dict literals
        if done_punish_level >= _level:
            final_punish_action = PUNISH_ACTION_LEVEL_MAP[_level]
        else:
            break
    return final_punish_action


# noinspection PyAbstractClass
class Event(Model):
    rcs_schema: dict = Field(..., title="事件参数定义")
    name: str = Field(max_length=25)
    desc: str = Field(max_length=50, title='事件描述')
    rules: List[ObjectId] = Field(default_factory=list, title="关联的规则id列表")
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    
    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}
    
    @classmethod
    def index_(cls):
        return [IndexModel('name', unique=True, name='idx_name_1')]

    # noinspection PyMethodParameters
    @validator("rcs_schema")
    def check_rcs_schema(cls, v) -> dict:
        try:
            EventSchema.parse(v)
        except Exception as e:
            logger.error(e)
            raise RCSExcErrArg(content=f"EventSchema parse failed {e}")
        return v

    @classmethod
    def validate_schema(cls, schema: dict, json: dict):
        try:
            rst = EventSchema.validate(schema, json)
        except Exception as e:
            return False, str(e)
        else:
            return True, rst

    async def fetch_strategy_latest_record(self, metric: str):
        from utils.fastapi_app import app
        # noinspection PyUnresolvedReferences
        records = await app.state.engine.gets(Record, Record.event == self.id,
                                              sort=Record.create_at.desc(), limit=1)
        # record = await Record.get_latest_by_event_id(event_id=self.id)
        if records:
            record = records[0]
        else:
            raise Exception('record not found')
        if record.event_data.get(metric) is not None:
            return record.event_data[metric]
        else:
            raise Exception('metric func not implemented')

    @classmethod
    async def clean(cls, event_id: Union[ObjectId, str]):
        event_id = ObjectId(event_id)
        from utils.fastapi_app import app
        rst = await app.state.engine.update_many(
            Scene, {Scene.events: {"$elemMatch": {"$eq": event_id}}},
            update={"$pull": {"rule": event_id}}
        )
        logger.info(rst)
        rst = await app.state.engine.delete_many(Record, Record.event == event_id)
        logger.info(rst)


# noinspection PyAbstractClass
class User(EmbeddedModel):
    user_id: str
    project: str


class ResultInRecord(EmbeddedModel):
    result_id: Optional[ObjectId] = Field(default=None, title='结果id')
    rule_id: ObjectId
    status: ResultInRecordStatus = Field(default=ResultInRecordStatus.WAIT, title="检测状态")
    punish_level: int = Field(default=0, title="风控等级")
    dispatch_time: datetime.datetime = Field(default=datetime.datetime.min, title="分发时间")
    done_time: datetime.datetime = Field(default=datetime.datetime.min, title="执行完成时间")


class PunishInRecord(EmbeddedModel):
    total_punish_level: int = Field(default=0, title="总风险等级")
    hit_punish_level: int = Field(default=0, title="已触发的风险等级")
    results_done: int = Field(default=0, title="已完成检查的规则数量")
    action: Action = Field(default=Action.NOTHING, title="惩罚动作")


# noinspection PyAbstractClass
class Record(Model):
    event: Event = Reference()
    event_data: dict = Field(..., title="事件数据")
    user: User = Field(..., title="用户信息")
    results: List[ResultInRecord] = Field(default_factory=list)
    punish: PunishInRecord = Field(default_factory=dict, title="惩罚")
    is_processed: bool = Field(default=False, title="是否已处理")
    event_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}

    @classmethod
    def index_(cls):
        return [IndexModel('name', unique=True, name='idx_name_1')]

    def reformat_event_data(self):
        rst, i = self.event.validate_schema(self.event.rcs_schema, self.event_data)
        if rst:
            self.event_data = i
        else:
            raise Exception(f'{Record} reformat_event_data failed')

    async def rules(self) -> Set[ObjectId]:
        rules = self.event.rules
        from utils.fastapi_app import app
        # noinspection PyUnresolvedReferences
        scene_rules = reduce(lambda a, b: a + b,
                             [scene.rules for scene in await app.state.engine.gets(
                                 Scene, Scene.events.in_([self.event.id]))])
        return set(rules) | set(scene_rules)

    def rules_punish_level(self) -> Dict[str, int]:
        """
        :return:
        """
        done_punish_level, total_punish_level = 0, 0
        for i in self.results:
            total_punish_level += i.punish_level
            if i.result_id:
                done_punish_level += i.punish_level

        return dict(done=done_punish_level, total=total_punish_level,
                    final_punish_action_sugguest=suggest_final_punishment(done_punish_level))

    def rules_check(self) -> Dict[ResultInRecordStatus, int]:
        # total_rules = len(self.results)
        # dispatched_rules = len([i for i in self.results if i.result_id])
        _d = dict(zip(ResultInRecordStatus, [0] * len(ResultInRecordStatus)))
        for _r in self.results:
            _d[_r.status] += 1
        _d['total'] = len(self.results)
        return _d

    @classmethod
    async def clean(cls, record_id: Union[ObjectId, str]):
        record_id = ObjectId(record_id)
        from utils.fastapi_app import app
        rst = await app.state.engine.delete_many(Result, Result.record == record_id)
        logger.info(rst)

    def a_dict(self, *args, **kwargs):
        d: dict = self.dict(*args, **kwargs)
        d['punish_level'] = self.rules_punish_level()
        d['checks_status'] = self.rules_check()
        return d


def serial_no_generator():
    """
    UTC timestamp, accurate to the millisecond
    :return:
    """
    return int(Dt.to_ts(Dt.utc_now()) * 1000)


class Handler(Model):
    name: str
    role: HandlerRole = Field(..., title="用户角色")
    encrypted_password: str = Field(..., title="密码(加密后)")
    token: str = Field(..., title="登录Token")
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}

    @classmethod
    def index_(cls):
        return [IndexModel('name', unique=True, name='idx_name_1')]


class Punishment(Model):
    record: Record = Reference()
    user: User
    action: Action = Field(..., title="处罚动作")
    details: dict = Field(default=dict(), title="详细")
    memo: str = Field('', max_length=20, title="备注")
    handler: Handler = Reference()
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    
    class Config:
        json_encoders = {Decimal: lambda x: str(x)}

# class Category(str, Enum):
#     registering = "registering"
#     sign_in = "sign_in"
#     crowdfunding = "crowdfunding"
#     mining_pool = "mining_pool"
#     financial_management = "financial_management"
#     recharge = "recharge"
#     withdraw = "withdraw"
#     currency_transaction = "currency_transaction"   # 币币交易
#     transfer = "transfer"
#     transaction_password = "transaction_password"

# noinspection PyAbstractClass
class Scene(Model):
    name: str = Field(max_length=128)
    desc: str = Field(max_length=128, title="场景描述/备注")
    events: List[ObjectId] = Field(default_factory=list)
    rules: List[ObjectId] = Field(default_factory=list)
    category: str = Field(..., title="场景类别", description="从config接口获取完整配置")
    scene_schema: dict = Field(..., title="场景参数定义")
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}

    @classmethod
    def index_(cls):
        return [IndexModel('name', unique=True, name='idx_name_1')]

    # noinspection PyMethodParameters
    @validator("scene_schema")
    def check_scene_schema(cls, v) -> dict:
        try:
            EventSchema.parse(v)
        except Exception as e:
            logger.exception(e)
            raise RCSExcErrArg(content="SceneSchema parse failed")
        return v

    @classmethod
    def validate_schema(cls, schema: dict, json: dict):
        try:
            rst = EventSchema.validate(schema, json)
        except Exception as e:
            return False, str(e)
        else:
            return True, rst

    async def fetch_strategy_latest_record(self, metric: str):
        from utils.fastapi_app import app
        # noinspection PyUnresolvedReferences
        records = await app.state.engine.gets(Record, Record.event == self.id,
                                              sort=Record.create_at.desc(), limit=1)
        # record = await Record.get_latest_by_event_id(event_id=self.id)
        if records:
            record = records[0]
        else:
            raise Exception('record not found')
        if record.event_data.get(metric) is not None:
            return record.event_data[metric]
        else:
            raise Exception('metric func not implemented')


# noinspection PyAbstractClass
class AggData(Model):
    scene: Scene = Reference()
    user: User
    agg_data: dict
    
    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}


# noinspection PyAbstractClass
class Config(Model):
    name: str = Field(primary_field=True)
    data: Union[List[Union[dict, str]], dict]
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}


# noinspection PyAbstractClass
class Rule(Model):
    rule: list = Field(default_factory=list, title="规则引擎规则")
    origin_rule: dict = Field(..., title="前端规则JSON")
    handler_name: str = Field(default='', title='用户name')
    name: str = Field(max_length=25)
    serial_no: int = Field(default_factory=serial_no_generator, title="规则序列号")
    user_prompt: str = Field(max_length=50, default='', title="用户提示")
    project: List[str] = Field(..., title="项目(列表)", description="从config接口获取完整配置")
    control_type: str = Field(..., title="控制类型/规则触发", description="从config接口获取完整配置")
    execute_type: str = Field(..., title="执行方式/风控方式", description="从config接口获取完整配置")
    punish_level: RulePunishLevel = Field(default=RulePunishLevel.level_1, title='风控等级/处罚等级', description="预设")
    punish_action: Action = Field(default=Action.REFUSE_OPERATION, title="风控手段/处罚方式", description="从config接口获取完整配置")
    punish_action_args: dict = Field(default_factory=dict, title="风控手段/处罚方式的参数")
    status: Status = Field(default=Status.OFF, title="状态", description="通过上下架接口更改")
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}

    @classmethod
    def index_(cls):
        return [IndexModel('name', unique=True, name='idx_name_1')]

    @root_validator(pre=True)
    def check_root(cls, values):
        values['rule'] = cls.translate_to_rule_engine_rule(values['origin_rule'])
        return values

    @validator('rule')
    def check_rule(cls, v):
        from utils.rule_operator import RuleParser
        RuleParser.validate(v)
        return v

    @validator('serial_no')
    def check_serial_no(cls, v):
        if not v or (isinstance(v, (float, int, Decimal, Decimal128)) and v <= 0):
            v = serial_no_generator()
        return v

    @classmethod
    def translate_to_rule_engine_rule(cls, origin_rule: dict) -> list:
        """
        Translate front-end rule JSON to RuleEngine format
        front-end rule JSON doc: https://tower.im/teams/713734/documents/19462/?fullscreen=true
        :return:
        """

        def _translate(rule: dict) -> list:
            """
            2021-08-24 modified
            {
                "key": "and", // 逻辑运算符， and、or
                "type": "",  // 可以为空，有值的情况见下面注释
                "value": "", // 可以为空，有值的情况见下面注释
                "source": "",  // 可以为空，有值的情况见下面注释
                "children": [
                    {
                        "key": "and",              // 逻辑运算符， and、or
                        "type": "withdraw",         // 类型，比如场景类别category（充币、提币）
                        "value": "single_withdrawal_amount_limit", // 输入值，比如场景名（提币1、充币2）
                        "source": "scene",     //  获取来源 ：场景或其它(待定)，暂时后端默认场景`scene`，后续待完善
                        "children": [
                            {
                                "argument": "amount",         // 场景参数名
                                "operator": ">=",        // 运算符
                                "value": "11",      // 场景参数的值
                                "unit": "个"     // 单位，可为空""（不显示）
                            },
                            {
                                "argument": "coin_name",
                                "operator": "=",
                                "value": "USDT-TRC20",
                                "unit": ""
                            }
                        ]
                    },
                     {
                        "key": "and",
                        "type": "recharge",
                        "value": "single_charge_amount_limit",
                        "source": "scene",
                        "children": [
                            {
                                "argument": "amount",
                                "operator": ">=",
                                "value": "11",
                                "unit": "个"
                            },
                            {
                                "argument": "coin_name",
                                "operator": "=",
                                "value": "USDT-TRC20",
                                "unit": ""
                            }
                        ]
                    }
                ]
            }
            :param rule:
            :return:
            """
            rst = []
            source = rule.get('source', 'scene')
            if rule.get('type') and source == 'scene':
                # ignore scene rule's `key`(and/or)
                # scene
                rst = [source, rule['value']]
                if not rule['children']:
                    raise RCSExcErrArg(f'no children in {rule["value"]}')
                for arg in rule['children']:
                    rst.append([arg['operator'], f"{source}::{arg['argument']}", arg['value']])
                return rst
            else:
                rst.append(rule['key'])
                for child in rule['children']:
                    child_rst = _translate(child)
                    rst.append(child_rst)
                return rst

        return _translate(origin_rule)

    @classmethod
    async def clean(cls, rule_id: Union[ObjectId, str]):
        rule_id = ObjectId(rule_id)
        from utils.fastapi_app import app
        rst = await app.state.engine.update_many(
            Scene, {"rules": {"$elemMatch": {"$eq": rule_id}}},
            update={"$pull": {"rules": rule_id}}
        )
        logger.info(rst)
        rst = await app.state.engine.update_many(
            Event, {"rules": {"$elemMatch": {"$eq": rule_id}}},
            update={"$pull": {"rules": rule_id}}
        )
        logger.info(rst)
        rst = await app.state.engine.delete_many(Result, Result.rule == rule_id)
        logger.info(rst)
        # Do delete from engine
        # await app.state.engine.delete(rule)


# noinspection PyAbstractClass
class Result(Model):
    rule: Rule = Reference()  # reference to rule
    record: Record = Reference()
    processed: bool = Field(default=False, title="是否已处理")
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}