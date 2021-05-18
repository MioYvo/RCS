# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/18/21 6:41 PM
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
from model.odm import Result, Event, User
from config import RCSExchangeName, DATA_PROCESSOR_ROUTING_KEY
from utils.fastapi_app import app
from utils.amqp_publisher import publisher
from utils.http_code import HTTP_201_CREATED
from utils.exceptions import RCSExcErrArg, RCSExcNotFound

router = APIRouter()


class ResultsOut(BaseModel):
    meta: dict
    content: Union[list, List[Result]]

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}


class ResultIn(BaseModel):
    event: ObjectId
    event_at: Optional[datetime] = PDField(default_factory=datetime.utcnow)
    event_data: dict
    user: User


class ResultOut(BaseModel):
    effect_published: bool





@router.put("/result/", response_model=ResultOut, status_code=HTTP_201_CREATED)
async def create_or_update_result(result_in: ResultIn):
    event: Optional[Event] = await app.state.engine.find_one(Event, Event.id == result_in.event)
    if not event:
        raise RCSExcNotFound(entity_id=str(result_in.event))
    # validate event
    validate_rst, validate_info = event.validate_schema(event.rcs_schema, result_in.event_data)
    if not validate_rst:
        raise RCSExcErrArg(content=validate_info)

    sending_data = result_in.dict()
    sending_data['event'] = event.dict()
    sending_data['event_data'] = validate_info

    tf, rst, sent_msg = await publisher(
        conn=app.state.amqp_connection,
        message=sending_data, exchange_name=RCSExchangeName,
        routing_key=DATA_PROCESSOR_ROUTING_KEY, timestamp=datetime.utcnow(),
    )
    return ResultOut(effect_published=tf)


@router.get("/result/")
async def get_results(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(default='event_at', description='must be attribute of Result model'),
        desc: bool = True, event_name: str = ""):

    _sort: FieldProxy = getattr(Result, sort, None)
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
        queries.append(Result.event.in_([e.id for e in events]))
        # !!! filter across references is not supported
        # queries.append(Result.event.name.match(name))
    # count to calculate total_page
    total_count = await app.state.engine.count(Result, *queries)
    results = await app.state.engine.gets(
        Result, *queries, sort=sort, skip=skip, limit=limit, return_doc=False)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(results))
    return YvoJSONResponse(
        dict(content=[i.dict() for i in results], meta=p.meta_pagination()),
    )


@router.get("/result/{result_id}", response_model=Result)
async def get_result(result_id: ObjectId):
    result = await app.state.engine.find_one(Result, Result.id == result_id)
    if not result:
        raise RCSExcNotFound(entity_id=str(result_id))
    return YvoJSONResponse(result.dict())


@router.delete("/result/{result_id}")
async def delete_result(result_id: ObjectId):
    result = await app.state.engine.find_one(Result, Result.id == result_id)
    if not result:
        raise RCSExcNotFound(entity_id=str(result_id))
    await app.state.engine.delete(result)
    return YvoJSONResponse(result.dict())
