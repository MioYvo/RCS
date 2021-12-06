# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/14/21 2:19 AM
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from typing import Union, List, Optional

from fastapi.params import Path
from pydantic import BaseModel, Field as PDField
from fastapi import APIRouter, Query
from odmantic import ObjectId
from odmantic.bson import BSON_TYPES_ENCODERS
from odmantic.field import FieldProxy
from odmantic.query import SortExpression

from Access.api.deps import Page, YvoJSONResponse
from SceneScript.statistic.withdraw_and_recharge import total_coins_amount, withdraw_address
from model.odm import Record, Event, User, PredefinedEventName, Rule
from config import RCSExchangeName, DATA_PROCESSOR_ROUTING_KEY
from utils.fastapi_app import app
from utils.amqp_publisher import publisher
from utils.http_code import HTTP_201_CREATED
from utils.exceptions import RCSExcErrArg, RCSExcNotFound, RCSUnexpectedErr
from utils.logger import Logger

router = APIRouter()
logger = Logger(__file__)


class RecordsOut(BaseModel):
    meta: dict
    content: Union[list, List[Record]]

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}


class RecordIn(BaseModel):
    event_name: str
    event_at: Optional[datetime] = PDField(default_factory=datetime.utcnow)
    event_data: dict = PDField(title='事件数据')
    user: User


class RecordOut(BaseModel):
    effect_published: bool


@router.put("/record/", response_model=RecordOut, status_code=HTTP_201_CREATED)
async def create_or_update_record(record_in: RecordIn):
    event: Optional[Event] = await app.state.engine.find_one(Event, Event.name == record_in.event_name)
    if not event:
        raise RCSExcNotFound(entity_id=str(record_in.event_name))
    # validate event
    validate_rst, validate_info = event.validate_schema(record_in.event_data)
    if not validate_rst:
        raise RCSExcErrArg(content=validate_info)

    sending_data = record_in.dict()
    sending_data['event'] = event.id
    # sending_data['event'] = event.dict()
    sending_data['event_data'] = validate_info

    tf, rst, sent_msg = await publisher(
        conn=app.state.amqp_connection,
        message=sending_data, exchange_name=RCSExchangeName,
        routing_key=DATA_PROCESSOR_ROUTING_KEY, timestamp=datetime.utcnow(),
    )
    return RecordOut(effect_published=tf)


@router.get("/record/")
async def get_records(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(default='event_at', description='must be attribute of Record model'),
        desc: bool = True,
        event_name: str = Query(default="", description="filter by Event.name"),
        all_data_view: bool = Query(default=False, description="是：显示所有记录，否：只显示需要审核的记录"),
        is_processed: Optional[bool] = Query(default=None, description="是：显示已处罚的记录，否：显示未处罚的记录"),
        relation_record_id: Union[ObjectId, str] = Query(
            default="", description="get specific record's related records"),

):
    _sort: FieldProxy = getattr(Record, sort, None)
    if not _sort:
        raise RCSExcErrArg(content=dict(sort=sort))
    sort: SortExpression = _sort.desc() if desc else _sort.asc()
    # skip
    skip = (page - 1) * per_page
    limit = per_page
    # build queries:
    queries = []
    if event_name:
        # noinspection PyUnresolvedReferences
        events = await app.state.engine.find(Event, Event.name.match(event_name) | Event.desc.match(event_name))
        # noinspection PyUnresolvedReferences
        queries.append(Record.event.in_([e.id for e in events]))
        # !!! filter across references is not supported
        # queries.append(Record.event.name.match(name))
    if relation_record_id:
        _record: Record = await app.state.engine.get_by_id(Record, relation_record_id)
        if not _record:
            raise RCSExcNotFound(entity_id=str(relation_record_id))
        queries += [Record.event_at < _record.event_at, Record.user == _record.user]
        # queries.append(Record.create_at < _record.create_at)
        # queries.append(Record.user.user_id == _record.user.user_id)
        # queries.append(Record.user.project == _record.user.project)
    if not all_data_view:
        queries.append({"results": {"$ne": [], "$elemMatch": {"result_id": {"$ne": None}}}})
    if is_processed is not None:
        queries.append(Record.is_processed == is_processed)

    logger.info(queries)
    # count to calculate total_page
    total_count = await app.state.engine.count(Record, *queries)
    records = await app.state.engine.find(
        Record, *queries, sort=sort, skip=skip, limit=limit)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(records))
    return YvoJSONResponse(
        dict(content=[await i.refer_dict(event_kwargs=dict(exclude={"rcs_schema", "rules"})) for i in records],
             meta=p.meta_pagination()),
    )


@router.get("/record/{record_id}", response_model=Record)
async def get_record(record_id: ObjectId):
    record = await app.state.engine.get_by_id(Record, record_id)
    if not record:
        raise RCSExcNotFound(entity_id=str(record_id))
    return YvoJSONResponse(await record.refer_dict())


@router.get("/record/{record_id}/results", description="记录相关规则执行的结果")
async def get_record_results(
        record_id: ObjectId = Path(..., description="记录id"),
        all_data_view: bool = Query(default=False, description="显示所有")

):
    record = await app.state.engine.get_by_id(Record, record_id)
    if not record:
        raise RCSExcNotFound(entity_id=str(record_id))

    _results = deepcopy(record.results)
    __results = []
    for _rst in _results:
        if not all_data_view and not _rst.result_id:
            continue
        _rule: Optional[Rule] = await app.state.engine.get_by_id(Rule, _rst.rule_id)
        if not _rule:
            continue
        __rst = {}
        __rst.update(_rst)
        __rst['rule'] = _rule.dict(exclude={"rule", "origin_rule", "create_at", "update_at"})
        __results.append(__rst)
    return YvoJSONResponse(__results)


@router.get("/record/{record_id}/statistics/withdraw", description="提币统计数据")
async def get_record_statistics_withdraw(record_id: ObjectId = Query(..., description="记录id")):
    record = await app.state.engine.get_by_id(Record, record_id)
    if not record:
        raise RCSExcNotFound(entity_id=str(record_id))

    # 充提币统计
    withdraw_event: Event = await app.state.engine.find_one(Event, Event.name == PredefinedEventName.withdraw)
    if not withdraw_event:
        raise RCSUnexpectedErr(content=f"event_id not found by event_name::"
                                       f"{PredefinedEventName.withdraw}:{withdraw_event}")

    return YvoJSONResponse(dict(
        total=await total_coins_amount(engine=app.state.engine, record=record, event=withdraw_event),
        address=await withdraw_address(engine=app.state.engine, record=record, withdraw_event=withdraw_event)
    ))


@router.get("/record/{record_id}/statistics/recharge", description="充值统计数据")
async def get_record_statistics_recharge(record_id: ObjectId = Query(..., description="记录id")):
    record = await app.state.engine.get_by_id(Record, record_id)
    if not record:
        raise RCSExcNotFound(entity_id=str(record_id))

    # 充提币统计
    recharge_event: Event = await app.state.engine.find_one(Event, Event.name == PredefinedEventName.recharge)
    if not recharge_event:
        raise RCSUnexpectedErr(content=f"event_id not found by event_name::"
                                       f"{PredefinedEventName.recharge}:{recharge_event}")

    return YvoJSONResponse(dict(
        total=await total_coins_amount(engine=app.state.engine, record=record, event=recharge_event)
    ))


@router.delete("/record/{record_id}")
async def delete_record(record_id: ObjectId):
    record = await app.state.engine.get_by_id(Record, record_id)
    if not record:
        raise RCSExcNotFound(entity_id=str(record_id))
    await app.state.engine.delete(record)
    await Record.clean(record_id)
    return YvoJSONResponse(record.dict())
