# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/30/21 6:04 PM
import json
import logging
from collections import defaultdict
from enum import Enum
from functools import reduce
from typing import Union, Optional, Dict, List

from bson import Decimal128, ObjectId
# from paco import map as paco_map

# from model.event import Event
from model.odm import Event
from utils.fastapi_app import app


class RuleEvaluationError(Exception):
    pass


class Functions(object):

    ALIAS = {
        '=': 'eq',
        '!=': 'neq',
        '>': 'gt',
        '>=': 'gte',
        '<': 'lt',
        '<=': 'lte',
        'and': 'and_',
        'in': 'in_',
        'or': 'or_',
        'not': 'not_',
        'str': 'str_',
        'int': 'int_',
        '+': 'plus',
        '-': 'minus',
        '*': 'multiply',
        '/': 'divide',
        'sce': 'scene'
    }

    @classmethod
    def convert_type(cls, args) -> list:
        args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, Decimal128):
                args[i] = arg.to_decimal()
        return args

    @classmethod
    def eq(cls, *args):
        args = cls.convert_type(args)
        return args[0] == args[1]

    @classmethod
    def neq(cls, *args):
        args = cls.convert_type(args)
        return args[0] != args[1]

    @classmethod
    def in_(cls, *args):
        args = cls.convert_type(args)
        return args[0] in args[1:]

    @classmethod
    def gt(cls, *args):
        args = cls.convert_type(args)
        return args[0] > args[1]

    @classmethod
    def gte(cls, *args):
        args = cls.convert_type(args)
        return args[0] >= args[1]

    @classmethod
    def lt(cls, *args):
        args = cls.convert_type(args)
        return args[0] < args[1]

    @classmethod
    def lte(cls, *args):
        args = cls.convert_type(args)
        return args[0] <= args[1]

    @classmethod
    def not_(cls, *args):
        args = cls.convert_type(args)
        return not args[0]

    @classmethod
    def or_(cls, *args):
        return any(args)

    @classmethod
    def and_(cls, *args):
        return all(args)

    @classmethod
    def int_(cls, *args):
        return int(args[0])

    @classmethod
    def str_(cls, *args):
        return str(args[0])

    @classmethod
    def upper(cls, *args):
        return args[0].upper()

    @classmethod
    def lower(cls, *args):
        return args[0].lower()

    @classmethod
    def plus(cls, *args):
        args = cls.convert_type(args)
        return sum(args)

    @classmethod
    def minus(cls, *args):
        args = cls.convert_type(args)
        # return args[0] - sum(args[1:])
        return reduce(lambda x, y: x - y, args)

    @classmethod
    def multiply(cls, *args):
        args = cls.convert_type(args)
        return reduce(lambda x, y: x * y, args)

    @classmethod
    def divide(cls, *args):
        args = cls.convert_type(args)
        return reduce(lambda x, y: x / y, args)
        # return float(args[0]) / float(args[1])

    @classmethod
    def abs(cls, *args):
        args = cls.convert_type(args)
        return abs(args[0])

    @classmethod
    def scene(cls, scene_id: str, *fields):
        pass



class FetchStrategy(Enum):
    latest_record = 'latest_record'


class RuleParser(object):
    DATA_PREFIX = "DATA::"
    REPLACE_PREFIX = "REPL::"

    def __init__(self, rule: Union[str, list], data: Optional[dict] = None):
        if isinstance(rule, str):
            self.rule = json.loads(rule)
        else:
            self.rule = rule
        self.data = data or {}
        self.validate(self.rule)

    @staticmethod
    def validate(rule):
        # TODO more validate info, args' type to compare with must be same type
        if not isinstance(rule, list):
            raise RuleEvaluationError('Rule must be a list, got {}'.format(type(rule)))
        if len(rule) < 2:
            raise RuleEvaluationError('Must have at least one argument.')

    @classmethod
    def coll_info(cls, rule: list) -> Dict[str, List[ObjectId]]:
        # TODO prevent cycle trigger executor
        def __coll_info(rl, _coll_mapping: Dict[str, set]):
            for rll in rl:
                if isinstance(rll, list):
                    __coll_info(rll, _coll_mapping)
                elif isinstance(rll, str) and rll.startswith(cls.DATA_PREFIX):
                    data_list = rll[len(cls.DATA_PREFIX):].split("::")
                    _coll_mapping[data_list[0]].add(ObjectId(data_list[1]))
        coll_mapping = defaultdict(set)
        __coll_info(rule, coll_mapping)
        coll_mapping = dict(coll_mapping)
        for k, v in coll_mapping.items():
            coll_mapping[k] = list(v)
        return coll_mapping

    @classmethod
    async def render_rule(cls, rule, data):
        # print(rule)
        for i, rl in enumerate(rule):
            if isinstance(rl, list):
                rule[i] = await cls.render_rule(rl, data)
            elif isinstance(rl, str) and rl.startswith(cls.DATA_PREFIX):
                rule[i] = await cls.get_data(rl)
            elif isinstance(rl, str) and rl.startswith(cls.REPLACE_PREFIX):
                rule[i] = cls.replace_data(rl, data)
            else:
                pass
        return rule

    @classmethod
    def replace_data(cls, arg: str, data):
        """
        replace schema arg with data
        :param arg: "REPL::key1::key1key1::..."
        :param data: {{"key1": {"key1key1": 123}, "key2": 321}}

        One record refers to many rules, and one rule contains many records, they are many2many relationship.
        Maybe this func will never be triggered.
        """
        arg_list = arg[len(cls.REPLACE_PREFIX):].split("::")
        for key in arg_list:
            data = data.get(key)
        return data

    @classmethod
    async def get_data(cls, arg: str):
        """
        get_data, format rule
        "DATA::event::456::amount::latest"

        :param arg: str "DATA::collection::coll_id::fetch_strategy::metric" startswith "DATA::"
        :return:
        """

        # arg: "DATA::event::60637cd71b57484ca719135e::latest_record::amount"
        data_list = arg[len(cls.DATA_PREFIX):].split("::")    # ['event', '456', 'latest_record', 'amount']
        assert len(data_list) in {3, 4}
        if len(data_list) == 3:
            data_list.append(FetchStrategy.latest_record.value)

        coll_name, coll_id, fetch_strategy, metric = data_list
        fetch_strategy: FetchStrategy = FetchStrategy(fetch_strategy)

        if coll_name == 'Event':
            event = await app.state.engine.find_one(Event, Event.id == ObjectId(coll_id))
            if not event:
                raise Exception(f'{coll_name}.{coll_id} not found')
            # event = await Event.get_by_id(_id=coll_id)
            fetch_strategy_fn = getattr(event, f"fetch_strategy_{fetch_strategy.value}")
            # to support different fetch_strategy, e.g latest_record or latest_N_record_avg
            metric_data = await fetch_strategy_fn(metric)  # no args
            return metric_data
        else:
            raise Exception(f'unsupported coll {coll_name}')

    def _evaluate(self, rule):
        """
        递归执行list内容
        """
        def _recurse_eval(arg):
            if isinstance(arg, list):
                return self._evaluate(arg)
            else:
                return arg

        r: list = list(map(_recurse_eval, rule))
        # print(f'rlist: {r}')
        func_name = Functions.ALIAS.get(r[0]) or r[0]
        func = getattr(Functions, func_name)
        return func(*r[1:])

    def evaluate(self) -> bool:
        ret = self._evaluate(self.rule)
        if not isinstance(ret, bool):
            logging.warning('In common usage, a rule must return a bool value,'
                            f'but get {ret}, please check the rule to ensure it is true')
        return ret

    @classmethod
    def evaluate_rule(cls, rule) -> bool:
        return cls(rule).evaluate()

    # TODO validate rule, args must be same type to compare with


if __name__ == '__main__':
    # ru = ['or', ['>', 1, 2], ['and', ['in_', 1, 1, 2, 3], ['>', 3, ['int', '2']]]]
    ru = ['or',
          ['>', 1, 2],
          ['and',
           ['in_', 1, 1, 2, 3],
           ['>', 100, ['int', '2']]]
          ]
    print(RuleParser.evaluate_rule(ru))

    ru = ['or',
          ['>', 1, 2],
          ['and',
           ['in_', 1, 1, "DATA::event::60637cd71b57484ca719135e::latest_record::user_id", 3],
           ['>', "DATA::event::60637cd71b57484ca719135e::latest_record::amount", ['int', '2']]]
          ]
    # rendered_rule = io_loop.run_until_complete(RuleParser.render_rule(ru))
    # print(rendered_rule)
    # print(RuleParser.evaluate_rule(rendered_rule))
    RuleParser.render_rule(ru, [])
    print('coll_info', RuleParser.coll_info(ru))
