# @Time : 2022-01-10 04:25:21
# @Author : Mio Lau
# @Contact: liurusi.101@gmail.com | github.com/MioYvo
# @File : recharge.py

from typing import Dict

from utils import Operator
from model.odm import Record
from SceneScript.register import scripts_manager
from SceneScript.bases.exchange import (
    num_per_time_limit, amount_per_time_limit,
)


@scripts_manager.register
async def lland_recharge_amount_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await amount_per_time_limit(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_name", "coin_contract_address", "token_id"),
        user_opt_names=("user_id", "project", "platform_id", "game_id", "chain_name"),
    )


@scripts_manager.register
async def lland_recharge_num_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await num_per_time_limit(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_name", "coin_contract_address", "token_id"),
        user_opt_names=("user_id", "project", "platform_id", "game_id", "chain_name"),
    )
