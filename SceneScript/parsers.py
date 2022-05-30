# @Time : 2022-01-12 10:23:28
# @Author : Mio Lau
# @Contact: liurusi.101@gmail.com | github.com/MioYvo
# @File : parsers.py
from typing import Dict, Iterable, Union, List

from odmantic.query import QueryExpression

from config import RULE_ENGINE_USER_DATA_FORMAT
from model.odm import Record
from utils import Operator


def parse_user_opt(
        kwargs: Dict[str, Operator],
        record: Record,
        opt_names: Iterable[str] = ("user_id", "project", "platform_id", "game_id", "chain_name")
) -> List[Union[QueryExpression, dict]]:
    queries = []
    for opt_name in opt_names:
        opt = kwargs.get(opt_name)
        if opt:
            if opt.data == RULE_ENGINE_USER_DATA_FORMAT:
                queries.append({
                    f"user.{opt.arg_name}": {
                        f"${opt.func_name.replace('_', '')}": getattr(record.user, opt.arg_name)
                    }
                })
            else:
                queries.append({
                    f"user.{opt.arg_name}": {
                        f"${opt.func_name.replace('_', '')}": opt.data
                    }
                })
    return queries


def parse_event_data_opt(
        kwargs: Dict[str, Operator],
        record: Record,
        opt_names: Iterable[str] = ("coin_contract_address", "token_id")
) -> List[Union[QueryExpression, dict]]:
    queries = []
    for opt_name in opt_names:
        opt = kwargs.get(opt_name)
        if opt:
            if opt.data == RULE_ENGINE_USER_DATA_FORMAT:
                queries.append({
                    f"event_data.{opt.arg_name}": {
                        f"${opt.func_name.replace('_', '')}": getattr(record.event_data, opt.arg_name)
                    }
                })
            else:
                queries.append({
                    f"event_data.{opt.arg_name}": {
                        f"${opt.func_name.replace('_', '')}": opt.data
                    }
                })
    return queries
