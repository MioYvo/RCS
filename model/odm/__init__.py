# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 6:27 PM
import datetime
from decimal import Decimal
from enum import Enum
from functools import reduce
from typing import List, Optional, Union

from loguru import logger
from pydantic import validator, root_validator
from pymongo import IndexModel
from odmantic import Model, ObjectId, Reference, Field, EmbeddedModel

from utils.exceptions import RCSExcErrArg
from utils.event_schema import EventSchema
from utils.gtz import Dt


# noinspection PyAbstractClass
class Event(Model):
    rcs_schema: dict = Field(..., title="事件参数定义")
    name: str = Field(max_length=25)
    rules: List[ObjectId] = Field(default_factory=list, title="关联的规则id列表")
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

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


# noinspection PyAbstractClass
class User(EmbeddedModel):
    user_id: str
    project: str


# noinspection PyAbstractClass
class Record(Model):
    event: Event = Reference()
    event_data: dict = Field(..., title="事件数据")
    user: User = Field(..., title="用户信息")
    event_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def index_(cls):
        return [IndexModel('name', unique=True, name='idx_name_1')]

    def reformat_event_data(self):
        rst, i = self.event.validate_schema(self.event.rcs_schema, self.event_data)
        if rst:
            self.event_data = i
        else:
            raise Exception(f'{+Record} reformat_event_data failed')

    async def rules(self) -> set:
        rules = self.event.rules
        from utils.fastapi_app import app
        # noinspection PyUnresolvedReferences
        scene_rules = reduce(lambda a, b: a + b,
                             [scene.rules for scene in await app.state.engine.gets(
                                    Scene, Scene.events.in_([self.event.id]))])
        return set(rules) | set(scene_rules)


class Status(str, Enum):
    ON = "on"
    OFF = "off"


def serial_no_generator():
    """
    UTC timestamp, accurate to the millisecond
    :return:
    """
    return int(Dt.to_ts(Dt.utc_now()) * 1000)


class HandlerRole(str, Enum):
    ADMIN = "admin"
    CUSTOMER_SERVICE = "customer_service"       # 客服


class Handler(Model):
    name: str
    role: HandlerRole = Field(..., title="用户角色")
    encrypted_password: str = Field(..., title="密码(加密后)")
    token: str = Field(..., title="登录Token")
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def index_(cls):
        return [IndexModel('name', unique=True, name='idx_name_1')]


class Action(str, Enum):
    BLOCK_USER = 'BLOCK_USER'
    BAN_USER_LOGIN = "BAN_USER_LOGIN"
    REFUSE_OPERATION = "REFUSE_OPERATION"


# noinspection PyAbstractClass
class Punishment(Model):
    results: List[ObjectId] = Field(..., title='关联的结果')
    action: str = Field(..., max_length=20, title="处罚动作")
    details: dict = Field(default=dict(), title="详细")
    memo: str = Field('', max_length=20, title="备注")
    handler: Handler = Reference()
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)


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


# noinspection PyAbstractClass
class Config(Model):
    name: str = Field(primary_field=True)
    data: Union[List[Union[dict, str]], dict]
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)


# noinspection PyAbstractClass
class Rule(Model):
    rule: list = Field(default_factory=list, title="规则引擎规则")
    origin_rule: dict = Field(..., title="前端规则JSON")
    handler_name: str = Field(default='', title='用户name')
    name: str = Field(max_length=25)
    serial_no: int = Field(default_factory=serial_no_generator, title="规则序列号")
    user_prompt: str = Field(max_length=50, default='', title="用户提示")
    project: str = Field(..., title="项目", description="从config接口获取完整配置")
    control_type: str = Field(..., title="控制类型/规则触发", description="从config接口获取完整配置")
    execute_type: str = Field(..., title="执行方式/风控方式", description="从config接口获取完整配置")
    status: Status = Field(default=Status.OFF, title="状态", description="通过上下架接口更改")
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    @classmethod
    def index_(cls):
        return [IndexModel('name', unique=True, name='idx_name_1')]

    @root_validator(pre=True)
    def check_root(cls, values):
        if not values.get('rule'):
            values['rule'] = cls.translate_to_rule_engine_rule(values['origin_rule'])
        return values

    @validator('rule')
    def check_rule(cls, v):
        from utils.rule_operator import RuleParser
        RuleParser.validate(v)
        return v

    @validator('serial_no')
    def check_serial_no(cls, v):
        if not v or (isinstance(v, (float, int, Decimal)) and v <= 0):
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
                        "type": "charge",
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
            if rule.get('type') and rule.get('source', 'scene') == 'scene':
                # ignore scene rule's `key`(and/or)
                # scene
                rst = [rule['source'], rule['value']]
                if not rule['children']:
                    raise RCSExcErrArg(f'no children in {rule["value"]}')
                for arg in rule['children']:
                    rst.append([arg['operator'], f"{rule['source']}::{arg['argument']}", arg['value']])
                return rst
            else:
                rst.append(rule['key'])
                for child in rule['children']:
                    child_rst = _translate(child)
                    rst.append(child_rst)
                return rst

        return _translate(origin_rule)


# noinspection PyAbstractClass
class Result(Model):
    rule: Rule = Reference()        # reference to event
    record: Record = Reference()
    processed: bool = Field(default=False, title="是否已处理")
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
