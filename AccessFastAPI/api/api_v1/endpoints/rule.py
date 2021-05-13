# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/14/21 2:19 AM
from fastapi import APIRouter, Query
from motor.core import AgnosticCollection
from odmantic import ObjectId
from odmantic.field import FieldProxy
from odmantic.query import SortExpression

from utils.rule_operator import RuleParser
from model.mapping import COLL_MAPPING
from utils.fastapi_app import app
from AccessFastAPI.api.deps import Page, YvoJSONResponse, RuleE
from utils.exceptions import RCSExcErrArg, RCSExcNotFound
from model.odm import Rule, Event
from utils.http_code import HTTP_201_CREATED

router = APIRouter()


@router.put("/rule/", response_model=Rule, status_code=HTTP_201_CREATED)
async def create_or_update_rule(rule: RuleE):
    _coll_info = RuleParser.coll_info(rule.rule)
    for k, v in _coll_info.items():
        coll = COLL_MAPPING.get(k)
        if not coll:
            raise RCSExcErrArg(content=f'Collection {k} not found')
        for coll_id in v:
            doc_obj = await app.state.engine.find_one(coll, coll.id == coll_id)
            if not doc_obj:
                raise RCSExcNotFound(entity_id=str(coll_id))

    rule = await app.state.engine.save(Rule(**rule.dict()))
    for k, v in _coll_info.items():
        coll = COLL_MAPPING[k]
        for coll_id in v:
            doc_obj = await app.state.engine.find_one(coll, coll.id == coll_id)
            # document_obj = await coll.get_by_id(_id=coll_id)
            doc_obj.rules.append(rule.id)
            await app.state.engine.save(doc_obj)
    return rule


@router.get("/rule/")
async def get_rules(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(default='update_at', description='must be attribute of Rule model'),
        desc: bool = True, name: str = ""):
    _sort: FieldProxy = getattr(Rule, sort, None)
    if not _sort:
        raise RCSExcErrArg(content=dict(sort=sort))
    sort: SortExpression = _sort.desc() if desc else _sort.asc()
    # skip
    skip = (page - 1) * per_page
    limit = per_page
    # build queries:
    queries = []
    if name:
        # noinspection PyUnresolvedReferences
        queries.append(Rule.name.match(name))
    # count to calculate total_page
    total_count = await app.state.engine.count(Rule, *queries)
    rules = await app.state.engine.gets(
        Rule, *queries, sort=sort, skip=skip, limit=limit, return_doc=False)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(rules))
    return YvoJSONResponse(
        dict(content=[i.dict() for i in rules], meta=p.meta_pagination()),
    )


@router.get("/rule/{rule_id}", response_model=Rule)
async def get_rule(rule_id: ObjectId):
    rule = await app.state.engine.find_one(Rule, Rule.id == rule_id)
    if not rule:
        raise RCSExcNotFound(entity_id=str(rule_id))
    return rule


@router.delete("/rule/{rule_id}", response_model=Rule)
async def delete_rule(rule_id: ObjectId):
    rule = await app.state.engine.find_one(Rule, Rule.id == rule_id)
    if not rule:
        raise RCSExcNotFound(entity_id=str(rule_id))

    # remove rule from all Event
    coll: AgnosticCollection = app.state.engine.get_collection(Event)
    await coll.update_many(
        {'rules': {"$elemMatch": {"$eq": rule_id}}},
        {
            '$pull': {'rules': rule_id}
        }
    )
    # events = app.state.engine.client.gets(Event, {"rules": {"$elemMatch": {"$eq": rule_id}}})
    await app.state.engine.delete(rule)
    return rule
