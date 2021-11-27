from datetime import timedelta
from bson import Decimal128 as Decimal
from typing import Dict

import loguru

from utils import Operator
from model.odm import Record
from utils.fastapi_app import app
from utils.gtz import Dt
from utils.yvo_engine import YvoEngine


async def single_amount_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')
    amount_opt: Operator = kwargs.get('amount')

    coin_name_rst = coin_name_opt.func(record.event_data.get('coin_name'), coin_name_opt.data) \
        if coin_name_opt else True

    if coin_name_rst:
        amount_rst = amount_opt.func(Decimal(str(record.event_data.get('amount'))), Decimal(str(amount_opt.data)))
        if amount_rst:
            return True
    return False


async def single_amount_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')
    amount_opt: Operator = kwargs.get('amount')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # noinspection PyTypeHints
    unit_of_time.data: timedelta
    # noinspection PyTypeHints
    app.state.engine: YvoEngine
    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event.id,
        Record.user.user_id == record.user.user_id,
        Record.user.project == record.user.project,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
        Record.create_at >= Dt.now() - unit_of_time.data,
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


async def single_num_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')
    number_opt: Operator = kwargs.get('number')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # noinspection PyTypeHints
    unit_of_time.data: timedelta
    # noinspection PyTypeHints
    app.state.engine: YvoEngine
    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event.id,
        Record.user.user_id == record.user.user_id,
        Record.user.project == record.user.project,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
        Record.create_at >= Dt.now() - unit_of_time.data,
        pipeline=[
            {"$group": {
                "_id": None,
                "total_number": {"$sum": 1}
            }},
            {"$project": {
                "total_number": 1
            }},
        ],
    )
    if rst:
        total_number = rst[0]['total_number']
        loguru.logger.info(total_number)
        amount_rst = number_opt.func(total_number, int(number_opt.data))
        if amount_rst:
            return True
    return False


async def project_amount_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')
    amount_opt: Operator = kwargs.get('amount')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # noinspection PyTypeHints
    unit_of_time.data: timedelta
    # noinspection PyTypeHints
    app.state.engine: YvoEngine
    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event.id,
        # Record.user.user_id == record.user.user_id,
        Record.user.project == record.user.project,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
        Record.create_at >= Dt.now() - unit_of_time.data,
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


async def project_num_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')
    number_opt: Operator = kwargs.get('number')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # noinspection PyTypeHints
    app.state.engine: YvoEngine
    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event.id,
        # Record.user.user_id == record.user.user_id,
        Record.user.project == record.user.project,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
        Record.create_at >= Dt.now() - timedelta(seconds=unit_of_time.data),
        pipeline=[
            {"$group": {
                "_id": None,
                "total_number": {"$sum": 1}
            }},
            {"$project": {
                "total_number": 1
            }},
        ],
    )
    if rst:
        total_number = rst[0]['total_number']
        loguru.logger.info(total_number)
        amount_rst = number_opt.func(total_number, int(number_opt.data))
        if amount_rst:
            return True
    return False


async def multi_stellar_address_to_one(
        record: Record,
        kwargs: Dict[str, Operator]) -> bool:
    coin_name_opt: Operator = kwargs.get('coin_name')
    number_opt: Operator = kwargs.get('number')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # noinspection PyTypeHints
    unit_of_time.data: timedelta

    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event.id,
        # Record.user.user_id == record.user.user_id,
        Record.user.project == record.user.project,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
        {"event_data.order_to": {"$eq": record.event_data['order_to']}},
        Record.create_at >= Dt.now() - unit_of_time.data,
        pipeline=[
            {"$group": {
                "_id": None,
                "user_ids": {"$addToSet": "$user.user_id"}
            }},
            {"$project": {
                "user_ids": 1
            }},
        ],
    )
    if rst:
        user_ids = rst[0]['user_ids']
        loguru.logger.info(user_ids)
        amount_rst = number_opt.func(len(user_ids), int(number_opt.data))
        if amount_rst:
            return True
    return False
