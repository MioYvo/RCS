# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 6:57 PM
from typing import Union, List

from pydantic import BaseModel
from fastapi import APIRouter, Query
from odmantic import ObjectId
from odmantic.bson import BSON_TYPES_ENCODERS
from odmantic.field import FieldProxy
from odmantic.query import SortExpression

from model.odm import Scene, SceneCategory
from Access.api.deps import Page
from utils.fastapi_app import app
from utils.http_code import HTTP_201_CREATED
from utils.exceptions import RCSExcErrArg, RCSExcNotFound


router = APIRouter()


class ScenesOut(BaseModel):
    meta: dict
    content: Union[list, List[Scene]]

    class Config:
        json_encoders = BSON_TYPES_ENCODERS


class ScenesCategoryOut(BaseModel):
    meta: dict
    content: Union[list, List[Scene]]

    class Config:
        json_encoders = BSON_TYPES_ENCODERS


@router.put("/scene/", response_model=Scene, status_code=HTTP_201_CREATED,
            description="""
## Create if no `id` field passed.
* `name` and `scene_schema` are required, other fields are optional.
## Update if `id` field passed.
* `created_at` and `update_time` will be ignored.
""")
async def create_or_update_scene(scene: Scene):
    if scene.dict(exclude_unset=True).get('id'):
        # Update
        exists_scene = await app.state.engine.find_one(Scene, Scene.id == scene.id)
        if exists_scene:
            new_update_ = Scene(**scene.dict(exclude={'update_at'})).dict(exclude={'create_at', 'id'})
            for name, value in new_update_.items():
                setattr(exists_scene, name, value)
            await app.state.engine.save(exists_scene)
            return exists_scene
        else:
            raise RCSExcNotFound(entity_id=str(scene.id))
    else:
        # Create
        # check
        await app.state.engine.save(scene)
        return scene


@router.get("/scene/", response_model=ScenesOut)
async def get_scenes(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(default='update_at', description='must be attribute of Scene model'),
        desc: bool = True, name: str = "", category: str = ""):

    _sort: FieldProxy = getattr(Scene, sort, None)
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
        queries.append(Scene.name.match(name))
    if category:
        queries.append(Scene.category.match(category))
    # count to calculate total_page
    total_count = await app.state.engine.count(Scene, *queries)
    scenes = await app.state.engine.gets(Scene, *queries, sort=sort, skip=skip, limit=limit,
                                         return_doc=False)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(scenes))
    # return YvoJSONResponse(
    #     dict(message='', error_code=0, content=scenes, meta=p.meta_pagination()),
    # )
    return dict(content=scenes, meta=p.meta_pagination())


# scene category
@router.get("/scene/category", response_model=ScenesCategoryOut)
async def get_scenes_category(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(
            default='name',
            description='must be attribute of SceneCategory model'
        ),
        desc: bool = True, name: str = ""):

    _sort: FieldProxy = getattr(SceneCategory, sort, None)
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
        queries.append(SceneCategory.name.match(name))
    # count to calculate total_page
    total_count = await app.state.engine.count(SceneCategory, *queries)
    scene_categories = await app.state.engine.gets(SceneCategory, *queries, sort=sort, skip=skip, limit=limit,
                                         return_doc=False)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(scene_categories))
    # return YvoJSONResponse(
    #     dict(message='', error_code=0, content=scenes, meta=p.meta_pagination()),
    # )
    return dict(content=scene_categories, meta=p.meta_pagination())


@router.put("/scene/category", response_model=SceneCategory, status_code=HTTP_201_CREATED,
            description="""
## Create if no `id` field passed.
* `name` and `scene_schema` are required, other fields are optional.
## Update if `id` field passed.
* `created_at` and `update_time` will be ignored.
""")
async def create_or_update_scene(scene_category: SceneCategory):
    if scene_category.dict(exclude_unset=True).get('id'):
        # Update
        exists_scene = await app.state.engine.find_one(SceneCategory, SceneCategory.id == scene_category.id)
        if exists_scene:
            new_update_ = SceneCategory(**scene_category.dict(exclude={'update_at'})).dict(exclude={'create_at', 'id'})
            for name, value in new_update_.items():
                setattr(exists_scene, name, value)
            await app.state.engine.save(exists_scene)
            return exists_scene
        else:
            raise RCSExcNotFound(entity_id=str(scene_category.id))
    else:
        # Create
        # check
        await app.state.engine.save(scene_category)
        return scene_category


@router.delete("/scene/category/{category_id}", response_model=SceneCategory)
async def delete_scene(category_id: ObjectId):
    scene_category = await app.state.engine.find_one(SceneCategory, SceneCategory.id == category_id)
    if not scene_category:
        raise RCSExcNotFound(entity_id=str(category_id))
    await app.state.engine.delete(scene_category)
    return scene_category


@router.get("/scene/{scene_id}", response_model=Scene)
async def get_scene(scene_id: ObjectId):
    scene = await app.state.engine.find_one(Scene, Scene.id == scene_id)
    if not scene:
        raise RCSExcNotFound(entity_id=str(scene_id))
    return scene


@router.delete("/scene/{scene_id}", response_model=Scene)
async def delete_scene(scene_id: ObjectId):
    scene = await app.state.engine.find_one(Scene, Scene.id == scene_id)
    if not scene:
        raise RCSExcNotFound(entity_id=str(scene_id))
    await app.state.engine.delete(scene)
    return scene