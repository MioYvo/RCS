# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/18/21 6:41 PM
from decimal import Decimal
from typing import Union, List

from pydantic import BaseModel, Field as PDField
from fastapi import APIRouter, Query, Depends
from odmantic import ObjectId
from odmantic.bson import BSON_TYPES_ENCODERS
from odmantic.field import FieldProxy
from odmantic.query import SortExpression

from Access.api.deps import Page, YvoJSONResponse, get_current_username
from model.odm import Punishment, Record, Rule, Action, Handler
from utils.fastapi_app import app
from utils.exceptions import RCSExcErrArg, RCSExcNotFound
from utils.http_code import HTTP_201_CREATED

router = APIRouter()


class PunishmentIn(BaseModel):
    results: List[ObjectId] = PDField(..., title='关联的结果id')
    action: Action = PDField(..., title='处罚动作')
    details: dict = PDField(default=dict(), title='详细信息（对象）')
    memo: str = PDField(default='', max_length=20, title="备注")


class PunishmentsOut(BaseModel):
    meta: dict
    content: Union[list, List[Punishment]]

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}


@router.put("/punishment/", response_model=Punishment, status_code=HTTP_201_CREATED,
            description="""
## Create if no `id` field passed.
* `name` and `rcs_schema` are required, other fields are optional.
## Update if `id` field passed.
* `created_at` and `update_time` will be ignored.
""")
async def create_or_update_event(punishment: Punishment, handler: Handler = Depends(get_current_username)):
    if punishment.dict(exclude_unset=True).get('id'):
        # Update
        exists_event = await app.state.engine.find_one(Punishment, Punishment.id == punishment.id)
        if exists_event:
            new_update_ = Punishment(**punishment.dict(exclude={'update_at'})).dict(exclude={'create_at', 'id'})
            for name, value in new_update_.items():
                setattr(exists_event, name, value)
            await app.state.engine.save(exists_event)
            return exists_event
        else:
            raise RCSExcNotFound(entity_id=str(punishment.id))
    else:
        # Create
        await app.state.engine.save(punishment)
        return punishment


@router.get("/punishment/")
async def get_punishments(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(default='create_at', description='must be attribute of Punishment model'),
        desc: bool = True, rule_name: str = ""):

    _sort: FieldProxy = getattr(Punishment, sort, None)
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
        rules = await app.state.engine.gets(Rule, Rule.name.match(rule_name))
        # noinspection PyUnresolvedReferences
        records = await app.state.engine.gets(Record, Record.event.in_(rules))  # FIXME
        # noinspection PyUnresolvedReferences
        queries.append(Punishment.record.in_([r.id for r in records]))
        # !!! filter across references is not supported
        # queries.append(Punishment.event.name.match(name))
    # count to calculate total_page
    total_count = await app.state.engine.count(Punishment, *queries)
    punishments = await app.state.engine.gets(
        Punishment, *queries, sort=sort, skip=skip, limit=limit, return_doc=False)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(punishments))
    return YvoJSONResponse(
        dict(content=[
            i.dict(exclude={'rule': {'rule', 'origin_rule'}, 'record': {'event': {'rcs_schema'}}}
                   ) for i in punishments], meta=p.meta_pagination()),
    )


@router.get("/punishment/{punishment_id}", response_model=Punishment)
async def get_result(punishment_id: ObjectId):
    punishment = await app.state.engine.find_one(Punishment, Punishment.id == punishment_id)
    if not punishment:
        raise RCSExcNotFound(entity_id=str(punishment_id))
    return YvoJSONResponse(punishment.dict())


@router.delete("/punishment/{punishment_id}")
async def delete_punishment(punishment_id: ObjectId):
    punishment = await app.state.engine.find_one(Punishment, Punishment.id == punishment_id)
    if not punishment:
        raise RCSExcNotFound(entity_id=str(punishment_id))
    await app.state.engine.delete(punishment)
    return YvoJSONResponse(punishment.dict())
