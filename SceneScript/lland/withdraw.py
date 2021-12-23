# @Time : 2022-01-10 04:25:16
# @Author : Mio Lau
# @Contact: liurusi.101@gmail.com | github.com/MioYvo
# @File : withdraw.py
from typing import Dict

from utils import Operator
from model.odm import Record
from SceneScript import scripts_manager
from SceneScript.bases.lland import contract_addr_num_per_time_limit
from SceneScript.bases.exchange import (
    num_per_time_limit, amount_per_time_limit,
    amount_limit, withdraw_without_recharge, multi_stellar_address_to_one)


@scripts_manager.register
async def lland_withdrawal_amount_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await amount_limit(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_name", "coin_contract_address", "token_id"),
        user_opt_names=("user_id", "project", "platform_id", "game_id", "chain_name")
    )


async def lland_withdraw_without_recharge(
        record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await withdraw_without_recharge(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_contract_address", "token_id"),
        user_opt_names=("user_id", "project", "platform_id", "game_id", "chain_name")
    )


@scripts_manager.register
async def lland_withdrawal_amount_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await amount_per_time_limit(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_name", "coin_contract_address", "token_id"),
        user_opt_names=("user_id", "project", "platform_id", "game_id", "chain_name"),
    )


@scripts_manager.register
async def lland_withdrawal_num_per_time_limit(
        record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await num_per_time_limit(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_name", "coin_contract_address", "token_id"),
        user_opt_names=("user_id", "project", "platform_id", "game_id", "chain_name"),
    )


@scripts_manager.register
async def lland_multi_address_withdraw_to_one(
        record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await multi_stellar_address_to_one(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_contract_address", "token_id"),
        user_opt_names=("user_id", "project", "platform_id", "game_id", "chain_name"),
    )


@scripts_manager.register
async def lland_withdrawal_contract_addr_num_per_time_limit(
        record: Record, kwargs: Dict[str, Operator]) -> bool:
    """
    单位时间内提卡数量限制
    :param record:
    :param kwargs:
    :return:
    """
    return await contract_addr_num_per_time_limit(
        record=record, kwargs=kwargs,
        event_data_opt_names=("coin_name", "token_id"),
        user_opt_names=("user_id", "project", "platform_id", "game_id", "chain_name"),
    )
