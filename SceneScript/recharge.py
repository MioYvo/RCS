from typing import Dict

from utils import Operator
from model.odm import Record
from SceneScript.register import scripts_manager
from SceneScript.recharge_withdraw_base import (
    single_amount_limit, single_amount_per_time_limit, single_num_per_time_limit,
    project_amount_per_time_limit, project_num_per_time_limit, multi_stellar_address_to_one
)


@scripts_manager.register
async def single_recharge_amount_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await single_amount_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def single_recharge_amount_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await single_amount_per_time_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def single_recharge_num_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    return await single_num_per_time_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def project_recharge_amount_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    return await project_amount_per_time_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def project_recharge_num_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    return await project_num_per_time_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def multi_stellar_address_recharge_to_one(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    return await multi_stellar_address_to_one(record=record, kwargs=kwargs)
