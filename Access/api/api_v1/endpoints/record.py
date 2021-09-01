# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/14/21 2:19 AM
from datetime import datetime
from decimal import Decimal
from typing import Union, List, Optional

from pydantic import BaseModel, Field as PDField
from fastapi import APIRouter, Query
from odmantic import ObjectId
from odmantic.bson import BSON_TYPES_ENCODERS
from odmantic.field import FieldProxy
from odmantic.query import SortExpression

from Access.api.deps import Page, YvoJSONResponse
from model.odm import Record, Event, User
from config import RCSExchangeName, DATA_PROCESSOR_ROUTING_KEY
from utils.fastapi_app import app
from utils.amqp_publisher import publisher
from utils.http_code import HTTP_201_CREATED
from utils.exceptions import RCSExcErrArg, RCSExcNotFound

router = APIRouter()


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
    validate_rst, validate_info = event.validate_schema(event.rcs_schema, record_in.event_data)
    if not validate_rst:
        raise RCSExcErrArg(content=validate_info)

    sending_data = record_in.dict()
    sending_data['event'] = event.dict()
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
        desc: bool = True, event_name: str = ""):

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
        events = await app.state.engine.gets(Event, Event.name.match(event_name))
        # noinspection PyUnresolvedReferences
        queries.append(Record.event.in_([e.id for e in events]))
        # !!! filter across references is not supported
        # queries.append(Record.event.name.match(name))
    # count to calculate total_page
    total_count = await app.state.engine.count(Record, *queries)
    records = await app.state.engine.gets(
        Record, *queries, sort=sort, skip=skip, limit=limit, return_doc=False)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(records))
    return YvoJSONResponse(
        dict(content=[i.dict() for i in records], meta=p.meta_pagination()),
    )


@router.get("/record/{record_id}", response_model=Record)
async def get_record(record_id: ObjectId):
    record = await app.state.engine.find_one(Record, Record.id == record_id)
    if not record:
        raise RCSExcNotFound(entity_id=str(record_id))
    return YvoJSONResponse(record.dict())


@router.delete("/record/{record_id}")
async def delete_record(record_id: ObjectId):
    record = await app.state.engine.find_one(Record, Record.id == record_id)
    if not record:
        raise RCSExcNotFound(entity_id=str(record_id))
    await app.state.engine.delete(record)
    await Record.clean(record_id)
    return YvoJSONResponse(record.dict())
