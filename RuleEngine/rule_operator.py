# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 3/30/21 6:04 PM
import json
import logging
from collections import defaultdict
from enum import Enum
from typing import Union, Optional, Dict, List

from bson import Decimal128, ObjectId
from paco import map as paco_map

from model.event import Event
from config.clients import io_loop


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
        '/': 'divide'
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
        return args[0] - args[1]

    @classmethod
    def multiply(cls, *args):
        args = cls.convert_type(args)
        return args[0] * args[1]

    @classmethod
    def divide(cls, *args):
        args = cls.convert_type(args)
        return float(args[0]) / float(args[1])

    @classmethod
    def abs(cls, *args):
        args = cls.convert_type(args)
        return abs(args[0])


class FetchStrategy(Enum):
    latest_record = 'latest_record'


class RuleParser(object):
    DATA_PREFIX = "DATA::"

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

    def _evaluate(self, rule):
        """
        递归执行list内容
        """
        def _recurse_eval(arg):
            if isinstance(arg, list):
                return self._evaluate(arg)
            else:
                return arg

        r = list(map(_recurse_eval, rule))
        # print(f'rlist: {r}')
        r[0] = Functions.ALIAS.get(r[0]) or r[0]
        func = getattr(Functions, r[0])
        return func(*r[1:])

    # @classmethod
    # async def render_rule(cls, rule):
    #     async def _render_rule(rule_arg: Union[str, list]):
    #         if isinstance(rule_arg, list):
    #             return await cls.render_rule(rule_arg)
    #         else:
    #             if isinstance(rule_arg, str) and rule_arg.startswith(cls.DATA_PREFIX):
    #                 return await cls.get_data(rule_arg)
    #             else:
    #                 return rule_arg
    #
    #     # noinspection PyUnresolvedReferences
    #     args = await paco_map(_render_rule, rule, loop=io_loop)
    #     return args

    @classmethod
    async def render_rule(cls, rule):
        # print(rule)
        for i, rl in enumerate(rule):
            if isinstance(rl, list):
                rule[i] = await cls.render_rule(rl)
            elif isinstance(rl, str) and rl.startswith(cls.DATA_PREFIX):
                rule[i] = await cls.get_data(rl)
            else:
                pass
        return rule

    @classmethod
    async def get_data(cls, arg: str):
        """
        get_data, format rule
        "DATA::event::456::amount::latest"

        :param arg: str "DATA::collection::coll_id::metric::fetch_strategy" startswith "DATA::"
        :return:
        """

        # arg: "DATA::event::60637cd71b57484ca719135e::latest_record::amount"
        data_list = arg[len(cls.DATA_PREFIX):].split("::")    # ['event', '456', 'latest_record', 'amount']
        assert len(data_list) in {3, 4}
        if len(data_list) == 3:
            data_list.append(FetchStrategy.latest.value)

        coll_name, coll_id, fetch_strategy, metric = data_list
        fetch_strategy: FetchStrategy = FetchStrategy(fetch_strategy)

        if coll_name == 'event':
            event = await Event.get_by_id(_id=coll_id)
            fetch_strategy_fn = getattr(event, f"fetch_strategy_{fetch_strategy.value}")
            # to support different fetch_strategy, e.g latest_record or latest_N_record_avg
            metric_data = await fetch_strategy_fn(metric)  # no args
            return metric_data
        else:
            raise Exception(f'unsupported coll {coll_name}')

    async def _async_evaluate(self, rule):
        """
        递归执行list内容
        """
        async def _recurse_eval(arg):
            if isinstance(arg, list):
                return await self._evaluate(arg)
            else:
                """
                ['or', ['>', "DATA::id::user_id", 2], ['and', ['in_', 1, 1, 2, 3], ['>', 3, ['int', '2']]]]
                """
                if isinstance(arg, str) and arg.startswith('DATA'):
                    await self.get_data(arg)
                return arg

        r = list(paco_map(_recurse_eval, rule, loop=io_loop))
        # print(f'rlist: {r}')
        r[0] = Functions.ALIAS.get(r[0]) or r[0]
        func = getattr(Functions, r[0])
        return func(*r[1:])

    def evaluate(self) -> bool:
        ret = self._evaluate(self.rule)
        if not isinstance(ret, bool):
            logging.warning('In common usage, a rule must return a bool value,'
                            'but get {}, please check the rule to ensure it is true')
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

    print('coll_info', RuleParser.coll_info(ru))
