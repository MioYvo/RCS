from decimal import Decimal
from typing import Dict, List

from model.odm import Record, Event
from utils.yvo_engine import YvoEngine


async def total_coins_amount(engine: YvoEngine, record: Record, events: List[Event]) -> List[Dict[str, Decimal]]:
    """
    充提币总额
    :param engine:
    :param record:
    :param events:
    :return:
    """
    _statistics = await engine.yvo_pipeline(
        Record,
        Record.user == record.user,
        Record.event.in_([event.id for event in events]),
        Record.event_at <= record.event_at,
        pipeline=[
            {
                "$group": {
                    "_id": "$event_data.coin_name",
                    "total": {"$sum": "$event_data.amount"}
                }
            }
        ]
    )
    return [{'coin': _r['_id'], 'total': _r['total']} for _r in _statistics]


async def withdraw_address(engine: YvoEngine, record: Record, withdraw_events: List[Event]):
    """
    {
        "user_count": 123,      # 向本地址提币的总用户数
        "address_count": 123,   # 向本地址提币的总次数
        "record_user_to_address_withdraw_count": 123,               # 本用户向本地址提币的次数
        "record_user_withdraw_count": 123,  # 用户历史提币次数
    }
    :param engine:
    :param record:
    :param withdraw_events:
    :return:
    """
    # 向本地址提币的总用户数
    _user_count = await engine.yvo_pipeline(
        Record,
        Record.event.in_([withdraw_event.id for withdraw_event in withdraw_events]),
        Record.event_at <= record.event_at,
        {"event_data.order_to": record.event_data['order_to']},
        pipeline=[
            {
                "$group": {
                    "_id": None,
                    "users": {"$addToSet": "$user"},
                    # "total": {"$sum": 1}
                }
            },
            {
                "$project": {"total_size": {"$size": "$users"}}
            }
        ]
    )
    user_count = _user_count[0]['total_size'] if _user_count else 0

    # 向本地址提币的总次数
    _address_count = await engine.yvo_pipeline(
        Record,
        Record.event.in_([withdraw_event.id for withdraw_event in withdraw_events]),
        Record.event_at <= record.event_at,
        {"event_data.order_to": record.event_data['order_to']},
        pipeline=[
            {
                "$group": {
                    "_id": None,
                    # "users": {"$addToSet": "user"},
                    "total": {"$sum": 1}
                }
            }
        ]
    )
    address_count = _address_count[0]['total'] if _address_count else 0

    # 本用户向本地址提币的次数
    _record_user_to_address_withdraw_count = await engine.yvo_pipeline(
        Record,
        Record.event.in_([withdraw_event.id for withdraw_event in withdraw_events]),
        Record.user == record.user,
        Record.event_at <= record.event_at,
        {"event_data.order_to": record.event_data['order_to']},
        pipeline=[
            {
                "$group": {
                    "_id": None,
                    # "users": {"$addToSet": "user"},
                    "total": {"$sum": 1}
                }
            }
        ]
    )
    record_user_to_address_withdraw_count = _record_user_to_address_withdraw_count[0]['total'] if _record_user_to_address_withdraw_count else 0

    # 用户历史提币次数
    _record_user_withdraw_count = await engine.yvo_pipeline(
        Record,
        Record.event.in_([withdraw_event.id for withdraw_event in withdraw_events]),
        Record.user == record.user,
        Record.event_at <= record.event_at,
        pipeline=[
            {
                "$group": {
                    "_id": None,
                    # "users": {"$addToSet": "user"},
                    "total": {"$sum": 1}
                }
            }
        ]
    )
    record_user_withdraw_count = _record_user_withdraw_count[0]['total'] if _record_user_withdraw_count else 0

    return dict(
        user_count=user_count,
        address_count=address_count,
        record_user_to_address_withdraw_count=record_user_to_address_withdraw_count,
        record_user_withdraw_count=record_user_withdraw_count
    )
