# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/14/21 2:19 AM
from collections import defaultdict

from fastapi import APIRouter, Query
from motor.core import AgnosticCollection
from odmantic import ObjectId
from odmantic.field import FieldProxy
from odmantic.query import SortExpression

from Access.api.deps import Page, YvoJSONResponse
from model.odm import Rule, Event, Result, Scene, Status
from model.mapping import COLL_MAPPING
from utils.fastapi_app import app
from utils.rule_operator import RuleParser
from utils.http_code import HTTP_201_CREATED
from utils.exceptions import RCSExcErrArg, RCSExcNotFound

router = APIRouter()


@router.put("/rule/", response_model=Rule, status_code=HTTP_201_CREATED, description="""
* `control_type` all options defined in [Config](/docs#/config/get_configs_api_v1_config__get), `name=rule_control_type`
* `execute_type` all options defined in [Config](/docs#/config/get_configs_api_v1_config__get), `name=rule_execute_type`
* `project` all options defined in [Config](/docs#/config/get_configs_api_v1_config__get), `name=project`
""")
async def create_or_update_rule(rule: Rule):
    _coll_info = RuleParser.coll_info(rule.rule)
    _instances = defaultdict(list)
    for k, v in _coll_info.items():
        coll = COLL_MAPPING.get(k)
        if not coll:
            raise RCSExcErrArg(content=f'Collection {k} not found')
        for coll_id in v:
            doc_obj = await app.state.engine.find_one(coll, coll.id == coll_id)
            if not doc_obj:
                raise RCSExcNotFound(entity_id=str(coll_id))
            else:
                _instances[coll].append(doc_obj)

    scenes = RuleParser.scene_info(rule.rule)
    # check scene
    for scene_name in scenes:
        scene = await app.state.engine.find_one(Scene, Scene.name == scene_name)
        if not scene:
            raise RCSExcNotFound(entity_id=str(scene_name))
        else:
            _instances[Scene].append(scene)

    rule = await app.state.engine.save(Rule(**rule.dict()))
    for _, instances in _instances.items():
        for instance in instances:
            instance.rules.append(rule.id)
            instance.rules = list(set(instance.rules))
            await app.state.engine.save(instance)
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


@router.delete("/rule/{rule_id}")
async def delete_rule(rule_id: ObjectId):
    rule = await app.state.engine.find_one(Rule, Rule.id == rule_id)
    if not rule:
        raise RCSExcNotFound(entity_id=str(rule_id))

    # del cache
    await app.state.engine.delete(rule)
    # remove rule from all Event
    await Rule.clean(rule_id)
    return YvoJSONResponse(
        dict(content=rule.dict()),
    )


@router.put("/rule/{rule_id}/status", response_model=Rule)
async def update_rule_status(rule_id: ObjectId, status: Status):
    rule = await app.state.engine.find_one(Rule, Rule.id == rule_id)
    if not rule:
        raise RCSExcNotFound(entity_id=str(rule_id))

    rule.status = status
    await app.state.engine.save(rule)
    return rule
