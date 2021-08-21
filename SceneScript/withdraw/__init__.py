from decimal import Decimal
from typing import Dict

from utils import Operator


async def single_withdrawal_amount_limit(event_data: dict, kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt = kwargs.get('coin_name')
    amount_opt = kwargs.get('amount')

    coin_name_rst = coin_name_opt.func(event_data.get('coin_name'), coin_name_opt.data) if coin_name_opt else True

    if coin_name_rst:
        amount_rst = amount_opt.func(Decimal(str(event_data.get('amount'))), Decimal(str(amount_opt.data)))
        if amount_rst:
            return True
    return False
