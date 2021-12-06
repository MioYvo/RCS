# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/18/21 6:41 PM
import datetime
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
    record: ObjectId
    action: Action = PDField(title="处罚动作", description="候选列表取自Config配置名punish_action",
                             example='REFUSE_OPERATION')
    details: dict = PDField(default=dict(), title="处罚详细参数 JSON对象",
                            description='时间区间处罚：候选列表取自Config配置名punish_action_args_seconds',
                            example='{"timedelta": 3600}')
    memo: str = PDField(default='', max_length=20, title="备注")


class PunishmentsOut(BaseModel):
    meta: dict
    content: Union[list, List[Punishment]]

    class Config:
        json_encoders = {Decimal: str, **BSON_TYPES_ENCODERS}


@router.put("/punishment/",
            response_model=Punishment,
            status_code=HTTP_201_CREATED,
            response_model_exclude={"handler": {"encrypted_password", "token"}},
            description="")
async def create_punishment(punishment: PunishmentIn, handler: Handler = Depends(get_current_username)):
    record = await app.state.engine.get_by_id(Record, punishment.record)
    if not record:
        raise RCSExcNotFound(entity_id=str(punishment.record))

    if punishment.details:
        _timedelta_arg = punishment.details.get('timedelta')
        if _timedelta_arg:
            _timedelta = datetime.timedelta(seconds=_timedelta_arg)
            _utc_now = datetime.datetime.utcnow()
            punishment.details['punishment_period'] = {
                "start": _utc_now, "end": _utc_now + _timedelta
            }
        else:
            punishment.details.pop("timedelta", None)
    new_punishment = Punishment(
        **punishment.dict(exclude={'update_at', 'record', 'handler'}),
        handler=handler.id, record=record.id, user=record.user
    )
    record.is_processed = True
    new_punishment, record = await app.state.engine.save_all([new_punishment, record])
    return YvoJSONResponse(new_punishment.dict(exclude={"handler": {"encrypted_password", "token"}}))


@router.get("/punishment/")
async def get_punishments(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(default='create_at', description='must be attribute of Punishment model'),
        desc: bool = True, rule_name: str = "",
        record_id: ObjectId = Query(default='', title="Record.id"),
        user_id: str = Query(default='', description="May come from Record.user.user_id"),
        project: str = Query(default='', description="May come from Record.user.project, <Config>")
):
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
        rules = await app.state.engine.find(Rule, Rule.name.match(rule_name))
        # noinspection PyUnresolvedReferences
        records = await app.state.engine.find(Record, Record.event.in_(rules))
        # noinspection PyUnresolvedReferences
        queries.append(Punishment.record.in_([r.id for r in records]))
        # !!! filter across references is not supported
        # queries.append(Punishment.event.name.match(name))
    if record_id:
        queries.append(Punishment.record == record_id)
    if user_id:
        queries.append(Punishment.user.user_id == user_id)
    if project:
        queries.append(Punishment.user.project == project)

    # count to calculate total_page
    total_count = await app.state.engine.count(Punishment, *queries)
    punishments = await app.state.engine.find(
        Punishment, *queries, sort=sort, skip=skip, limit=limit)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(punishments))
    return YvoJSONResponse(
        dict(content=[await i.refer_dict(
            record_kwargs=dict(
                event_kwargs=dict(
                    exclude={'rcs_schema'}
                ),
                exclude={'results'}
        )) for i in punishments],
             meta=p.meta_pagination())
    )


@router.get("/punishment/{punishment_id}", response_model=Punishment)
async def get_punishment(punishment_id: ObjectId):
    punishment = await app.state.engine.get_by_id(Punishment, punishment_id)
    if not punishment:
        raise RCSExcNotFound(entity_id=str(punishment_id))
    return YvoJSONResponse(await punishment.refer_dict())


@router.delete("/punishment/{punishment_id}", status_code=204)
async def delete_punishment(punishment_id: ObjectId):
    punishment = await app.state.engine.get_by_id(Punishment, punishment_id)
    if not punishment:
        raise RCSExcNotFound(entity_id=str(punishment_id))
    await app.state.engine.delete(punishment)
    return YvoJSONResponse(punishment.dict())
