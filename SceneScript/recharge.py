from typing import Dict

from utils import Operator
from model.odm import Record
from SceneScript.register import scripts_manager
from SceneScript.withdraw import single_withdrawal_amount_limit, single_withdrawal_amount_per_time_limit


async def single_recharge_amount_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await single_withdrawal_amount_limit(record=record, kwargs=kwargs)


@scripts_manager.register
async def single_recharge_amount_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    return await single_withdrawal_amount_per_time_limit(record=record, kwargs=kwargs)
