# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 6:57 PM
from typing import Union, List

from pydantic import BaseModel
from fastapi import APIRouter, Query
from odmantic.bson import BSON_TYPES_ENCODERS

from model.odm import Config
from Access.api.deps import Page
from utils.fastapi_app import app
from utils.http_code import HTTP_201_CREATED
from utils.exceptions import RCSExcNotFound


router = APIRouter()


class ConfigIn(BaseModel):
    name: str
    data: Union[list, dict]


class ConfigsOut(BaseModel):
    meta: dict
    content: Union[list, List[Config]]

    class Config:
        json_encoders = BSON_TYPES_ENCODERS


class ConfigsCategoryOut(BaseModel):
    meta: dict
    content: Union[list, List[Config]]

    class Config:
        json_encoders = BSON_TYPES_ENCODERS


@router.put("/config/", response_model=Config, status_code=HTTP_201_CREATED,
            description="""
* `name` and `data` are required, other fields are optional.
* `created_at` and `update_time` will be ignored.
* *Update* if `name` exits in db, otherwise *Create* new one.
""")
async def create_or_update_config(config: ConfigIn):
    _config = await app.state.engine.save(Config(**config.dict(exclude={'update_at'})))
    return _config


@router.get("/config/", response_model=ConfigsOut)
async def get_configs(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        name: str = ""):

    # skip
    skip = (page - 1) * per_page
    limit = per_page
    # build queries:
    queries = []
    if name:
        # noinspection PyUnresolvedReferences
        queries.append(Config.name.match(name))
    # count to calculate total_page
    total_count = await app.state.engine.count(Config, *queries)
    configs = await app.state.engine.find(Config, *queries, skip=skip, limit=limit)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(configs))
    # return YvoJSONResponse(
    #     dict(message='', error_code=0, content=configs, meta=p.meta_pagination()),
    # )
    return dict(content=configs, meta=p.meta_pagination())


@router.get("/config/{config_name}", response_model=Config)
async def get_config(config_name: str):
    config = await app.state.engine.get_by_id(Config, Config.name == config_name)
    if not config:
        raise RCSExcNotFound(entity_id=config_name)
    return config


@router.delete("/config/{config_name}", response_model=Config)
async def delete_config(config_name: str):
    config = await app.state.engine.get_by_id(Config, Config.name == config_name)
    if not config:
        raise RCSExcNotFound(entity_id=config_name)
    await app.state.engine.delete(config)
    return config
