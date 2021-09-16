from typing import Dict, Optional

from utils import Operator
from utils.fastapi_app import app
from model.odm import Record, Event
from SceneScript import scripts_manager
from SceneScript.recharge_withdraw_base import (
    single_amount_limit, single_amount_per_time_limit, single_num_per_time_limit,
    project_amount_per_time_limit, project_num_per_time_limit, multi_stellar_address_to_one
)


async def single_withdraw_without_recharge(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')

    recharge_event: Optional[Event] = await app.state.engine.find_one(
        Event,
        Event.name == 'recharge'
    )
    if not recharge_event:
        raise Exception('Recharge event NOT FOUND')
    first_one = await app.state.engine.find_one(
        Record,
        Record.event == recharge_event.id,
        Record.user.user_id == record.user.user_id,
        Record.user.project == record.user.project,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
    )
    return False if first_one else True


@scripts_manager.register
async def single_withdrawal_amount_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await single_amount_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def single_withdrawal_amount_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await single_amount_per_time_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def single_withdrawal_num_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    return await single_num_per_time_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def project_withdrawal_amount_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    return await project_amount_per_time_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def project_withdrawal_num_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    return await project_num_per_time_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def multi_stellar_address_withdraw_to_one(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    return await multi_stellar_address_to_one(record=record, kwargs=kwargs)
