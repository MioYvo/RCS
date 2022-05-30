"""
Exchange(充提币) Recharge(充币) 场景脚本
"""
from typing import Dict

from utils import Operator
from model.odm import Record
from SceneScript.register import scripts_manager
from SceneScript.bases.exchange import (
    amount_limit, amount_per_time_limit, num_per_time_limit, multi_stellar_address_to_one
)


@scripts_manager.register
async def exchange_recharge_amount_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await amount_limit(
        record=record, kwargs=kwargs,
        user_opt_names=("user_id", "project"),
        event_data_opt_names=("coin_name", )
    )


@scripts_manager.register
async def exchange_recharge_amount_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await amount_per_time_limit(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_name", ), user_opt_names=("user_id", "project")
    )


@scripts_manager.register
async def exchange_recharge_num_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await num_per_time_limit(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_name", ), user_opt_names=("user_id", "project")
    )


@scripts_manager.register
async def exchange_recharge_multi_stellar_address_to_one(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await multi_stellar_address_to_one(
        record=record, kwargs=kwargs,
        event_data_opt_names=(), user_opt_names=("user_id", "project")
    )
