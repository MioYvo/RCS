# @Time : 2022-01-10 03:33:08
# @Author : Mio Lau
# @Contact: liurusi.101@gmail.com | github.com/MioYvo
# @File : lland.py
from decimal import Decimal
from typing import Dict, Iterable

import loguru

from SceneScript.parsers import parse_event_data_opt, parse_user_opt
from model.odm import Record
from utils import Operator
from utils.gtz import Dt
from utils.fastapi_app import app


async def contract_addr_num_per_time_limit(
        record: Record, kwargs: Dict[str, Operator],
        event_data_opt_names: Iterable[str] = ("coin_contract_address", "token_id"),
        user_opt_names: Iterable[str] = ("user_id", "platform_id", "game_id", "chain_name")
) -> bool:
    """
    单位时间内提卡数量限制
    :param user_opt_names:
    :param event_data_opt_names: Tuple[str]
    :param record:
    :param kwargs:
    :return:
    """
    number_opt: Operator = kwargs.get('number')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # event_data <Optional> opt
    event_data_queries = parse_event_data_opt(
        kwargs, record, opt_names=event_data_opt_names)
    # user <Optional> opt
    user_queries = parse_user_opt(kwargs, record, opt_names=user_opt_names)

    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event,
        Record.create_at >= Dt.now() - unit_of_time.data,
        *event_data_queries,
        *user_queries,
        pipeline=[
            {"$group": {
                "_id": None,
                "contract_addresses": {"$addToSet": "$event_data.coin_contract_address"}
            }},
            {"$project": {
                "contract_addresses": 1
            }},
        ],
    )
    if rst:
        contract_addresses = rst[0]['contract_addresses']
        loguru.logger.info(contract_addresses)
        amount_rst = number_opt.func(len(contract_addresses), int(number_opt.data))
        if amount_rst:
            return True
    return False
