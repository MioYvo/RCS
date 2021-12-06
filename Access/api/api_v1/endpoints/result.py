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
from model.odm import Result, User, Record, Rule
from utils.fastapi_app import app
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


@router.get("/result/")
async def get_results(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(default='create_at', description='must be attribute of Result model'),
        desc: bool = True, rule_name: str = "",
        record_id: ObjectId = Query(default="", description='Record.id')
):
    _sort: FieldProxy = getattr(Result, sort, None)
    if not _sort:
        raise RCSExcErrArg(content=dict(sort=sort))
    sort: SortExpression = _sort.desc() if desc else _sort.asc()
    # skip
    skip = (page - 1) * per_page
    limit = per_page
    # build queries:
    queries = []
    if rule_name:
        # TODO filter records by rule_name
        # noinspection PyUnresolvedReferences
        rules = await app.state.engine.find(Rule, Rule.name.match(rule_name))
        # noinspection PyUnresolvedReferences
        records = await app.state.engine.find(Record, Record.event.in_(rules))
        # noinspection PyUnresolvedReferences
        queries.append(Result.record.in_([r.id for r in records]))
        # !!! filter across references is not supported
        # queries.append(Result.event.name.match(name))
    if record_id:
        queries.append(Result.record == record_id)
    # count to calculate total_page
    total_count = await app.state.engine.count(Result, *queries)
    results = await app.state.engine.find(
        Result, *queries, sort=sort, skip=skip, limit=limit)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(results))
    return YvoJSONResponse(
        dict(content=[
            await i.refer_dict(
                record_kwargs=dict(exclude={'event': {'rcs_schema'}}),
                rule_kwargs=dict(exclude={'rule', 'origin_rule'})
            ) for i in results], meta=p.meta_pagination()),
    )


@router.get("/result/{result_id}", response_model=Result)
async def get_result(result_id: ObjectId):
    result = await app.state.engine.get_by_id(Result, result_id)
    if not result:
        raise RCSExcNotFound(entity_id=str(result_id))
    return YvoJSONResponse(await result.refer_dict())


@router.delete("/result/{result_id}")
async def delete_result(result_id: ObjectId):
    raise RCSExcErrArg("Result cannot be deleted :(")
    # result = await app.state.engine.get_by_id(Result, result_id)
    # if not result:
    #     raise RCSExcNotFound(entity_id=str(result_id))
    # await app.state.engine.delete(result)
    # return YvoJSONResponse(result.dict())
