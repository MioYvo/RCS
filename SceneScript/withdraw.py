from datetime import timedelta
from bson import Decimal128 as Decimal
from typing import Dict

import loguru

from SceneScript.register import scripts_manager
from utils import Operator
from model.odm import Record
from utils.fastapi_app import app
from utils.gtz import Dt
from utils.yvo_engine import YvoEngine


async def single_withdrawal_amount_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')
    amount_opt: Operator = kwargs.get('amount')

    coin_name_rst = coin_name_opt.func(record.event_data.get('coin_name'), coin_name_opt.data) if coin_name_opt else True

    if coin_name_rst:
        amount_rst = amount_opt.func(Decimal(str(record.event_data.get('amount'))), Decimal(str(amount_opt.data)))
        if amount_rst:
            return True
    return False


@scripts_manager.register
async def single_withdrawal_amount_per_time_limit(record: Record, kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')
    amount_opt: Operator = kwargs.get('amount')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # noinspection PyTypeHints
    unit_of_time.data: int      # seconds
    # noinspection PyTypeHints
    app.state.engine: YvoEngine
    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event.id,
        Record.user.user_id == record.user.user_id,
        Record.user.project == record.user.project,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
        Record.create_at >= Dt.now() - timedelta(seconds=unit_of_time.data),
        # pipeline=[
        #     {"$group": {
        #         "_id": None,
        #         "total_amount": {"$sum": "$event_data.amount"}
        #     }},
        #     {"$project": {
        #         "total_amount": 1
        #     }},
        # ],
    )
    loguru.logger.info(rst)

    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event.id,
        Record.user.user_id == record.user.user_id,
        Record.user.project == record.user.project,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
        Record.create_at >= Dt.now() - timedelta(seconds=unit_of_time.data),
        pipeline=[
            {"$group": {
                "_id": None,
                "total_amount": {"$sum": "$event_data.amount"}
            }},
            {"$project": {
                "total_amount": 1
            }},
        ],
    )
    if rst:
        amount = rst[0]['total_amount']
        loguru.logger.info(amount)
        amount_rst = amount_opt.func(Decimal(str(amount)), Decimal(str(amount_opt.data)))
        if amount_rst:
            return True
    return False
