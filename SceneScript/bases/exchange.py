from bson import Decimal128 as Decimal
from typing import Dict, Iterable, Optional

from loguru import logger as logging

from SceneScript.parsers import parse_user_opt, parse_event_data_opt
from config import RULE_ENGINE_USER_DATA_FORMAT
from model.odm import Record, Event, PredefinedEventName
from utils import Operator
from utils.fastapi_app import app
from utils.gtz import Dt


async def amount_limit(
        record: Record,
        kwargs: Dict[str, Operator],
        event_data_opt_names: Iterable[str] = (),
        user_opt_names: Iterable[str] = ()
) -> bool:
    # <Required> opt
    amount_opt: Operator = kwargs.get('amount')
    # <Optional> opt
    # event_data_opt_names = ("coin_name", "coin_contract_address", "token_id")
    for opt_name in event_data_opt_names:
        opt = kwargs.get(opt_name)
        if opt and opt.data != RULE_ENGINE_USER_DATA_FORMAT and not opt.func(record.event_data.get(opt_name), opt.data):
            return False
    # <Optional> user opt
    # event_data_opt_names = ("user_id", "project", "platform_id", "game_id", "chain_name")
    for opt_name in user_opt_names:
        opt = kwargs.get(opt_name)
        if opt and opt.data != RULE_ENGINE_USER_DATA_FORMAT and not opt.func(getattr(record.user, opt_name), opt.data):
            return False
    # amount opt func
    amount_rst = amount_opt.func(Decimal(str(record.event_data.get('amount'))), Decimal(str(amount_opt.data)))
    if amount_rst:
        return True
    return False


async def amount_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator],
        event_data_opt_names: Iterable[str] = ("coin_name", "coin_contract_address", "token_id"),
        user_opt_names: Iterable[str] = ("user_id", "project", "platform_id", "game_id", "chain_name")
) -> bool:
    # <Required> opt
    amount_opt: Operator = kwargs.get('amount')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # <Optional> evnet_data opt
    event_data_queries = parse_event_data_opt(kwargs, record, opt_names=event_data_opt_names)
    # <Optional> user opt
    user_queries = parse_user_opt(kwargs, record, opt_names=user_opt_names)

    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event,
        Record.create_at >= Dt.now() - unit_of_time.data,
        *user_queries,
        *event_data_queries,
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
        logging.info(f"{amount=}")
        amount_rst = amount_opt.func(Decimal(str(amount)), Decimal(str(amount_opt.data)))
        if amount_rst:
            return True
    return False


async def num_per_time_limit(
        record: Record,
        kwargs: Dict[str, Operator],
        event_data_opt_names: Iterable[str] = (),
        user_opt_names: Iterable[str] = ()
) -> bool:
    # <Required> opt
    number_opt: Operator = kwargs.get('number')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # <Optional> evnet_data opt
    event_data_queries = parse_event_data_opt(kwargs, record, opt_names=event_data_opt_names)
    # <Optional> user opt
    user_queries = parse_user_opt(kwargs, record, opt_names=user_opt_names)
    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event,
        Record.create_at >= Dt.now() - unit_of_time.data,
        *user_queries,
        *event_data_queries,
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
        logging.info(f"{total_number=}")
        amount_rst = number_opt.func(total_number, int(number_opt.data))
        if amount_rst:
            return True
    return False


async def withdraw_without_recharge(
        record: Record, kwargs: Dict[str, Operator],
        event_data_opt_names: Iterable[str] = (),
        user_opt_names: Iterable[str] = ()
) -> bool:
    # <Required> opt
    coin_name_opt: Operator = kwargs.get('coin_name')
    # <Optional> event_data opt
    event_data_queries = parse_event_data_opt(
        kwargs, record, opt_names=event_data_opt_names)
    # <Optional> user opt
    user_queries = parse_user_opt(kwargs, record, opt_names=user_opt_names)

    # noinspection PyUnresolvedReferences
    recharge_events: List[Optional[Event]] = await app.state.engine.find(
        Event,
        Event.name.in_(PredefinedEventName.recharge_list())
    )
    if not recharge_events:
        raise Exception('Recharge event NOT FOUND')
    # noinspection PyUnresolvedReferences
    logging.info(f"{event_data_queries=}, {user_queries=}")
    first_one = await app.state.engine.find_one(
        Record,
        Record.event.in_([recharge_event.id for recharge_event in recharge_events]),
        *event_data_queries,
        *user_queries,
        {"event_data.coin_name": {f"${coin_name_opt.func_name.replace('_', '')}": coin_name_opt.data}},
    )
    return False if first_one else True


async def multi_stellar_address_to_one(
        record: Record,
        kwargs: Dict[str, Operator],
        event_data_opt_names: Iterable[str] = ("coin_name", "coin_contract_address", "token_id"),
        user_opt_names: Iterable[str] = ("user_id", "platform_id", "game_id", "chain_name")
) -> bool:
    # <Required> opt
    number_opt: Operator = kwargs.get('number')
    unit_of_time: Operator = kwargs.get('unit_of_time')
    # <Optional> evnet_data opt
    event_data_queries = parse_event_data_opt(kwargs, record, opt_names=event_data_opt_names)
    # <Optional> user opt
    user_queries = parse_user_opt(kwargs, record, opt_names=user_opt_names)

    rst = await app.state.engine.yvo_pipeline(
        Record,
        Record.event == record.event,
        {"event_data.order_to": {"$eq": record.event_data['order_to']}},
        Record.create_at >= Dt.now() - unit_of_time.data,
        *event_data_queries,
        *user_queries,
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
        logging.info(user_ids)
        amount_rst = number_opt.func(len(user_ids), int(number_opt.data))
        if amount_rst:
            return True
    return False
