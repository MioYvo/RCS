# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 6:57 PM
import logging
from typing import Union, List

from pydantic import BaseModel
from fastapi import APIRouter, Query
from odmantic import ObjectId
from odmantic.bson import BSON_TYPES_ENCODERS
from odmantic.field import FieldProxy
from odmantic.query import SortExpression

from model.odm import Event
from Access.api.deps import Page
from utils.fastapi_app import app
from utils.http_code import HTTP_201_CREATED
from utils.exceptions import RCSExcErrArg, RCSExcNotFound


router = APIRouter()


class EventsOut(BaseModel):
    meta: dict
    content: Union[list, List[Event]]

    class Config:
        json_encoders = BSON_TYPES_ENCODERS


@router.put("/event/", response_model=Event, status_code=HTTP_201_CREATED,
            description="""
## Create if no `id` field passed.
* `name` and `rcs_schema` are required, other fields are optional.
## Update if `id` field passed.
* `created_at` and `update_time` will be ignored.
""")
async def create_or_update_event(event: Event):
    if event.dict(exclude_unset=True).get('id'):
        # Update
        exists_event = await app.state.engine.find_one(Event, Event.id == event.id)
        if exists_event:
            new_update_ = Event(**event.dict(exclude={'update_at'})).dict(exclude={'create_at', 'id'})
            for name, value in new_update_.items():
                setattr(exists_event, name, value)
            await app.state.engine.save(exists_event)
            return exists_event
        else:
            raise RCSExcNotFound(entity_id=str(event.id))
    else:
        # Create
        await app.state.engine.save(event)
        return event


@router.get("/event/", response_model=EventsOut)
async def get_events(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = Query(default='update_at', description='must be attribute of Event model'),
        desc: bool = True,
        name: str = ""):

    _sort: FieldProxy = getattr(Event, sort, None)
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
        queries.append(Event.name.match(name) | Event.desc.match(name))
    # count to calculate total_page
    total_count = await app.state.engine.count(Event, *queries)
    logging.info(total_count)
    events = await app.state.engine.find(Event, *queries, sort=sort, skip=skip, limit=limit)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(events))
    # return YvoJSONResponse(
    #     dict(message='', error_code=0, content=events, meta=p.meta_pagination()),
    # )
    return dict(content=events, meta=p.meta_pagination())


@router.get("/event/{event_id}", response_model=Event)
async def get_event(event_id: ObjectId):
    event = await app.state.engine.get_by_id(Event, event_id)
    if not event:
        raise RCSExcNotFound(entity_id=str(event_id))
    return event


@router.delete("/event/{event_id}", status_code=204)
async def delete_event(event_id: ObjectId):
    event = await app.state.engine.get_by_id(Event, event_id)
    if not event:
        raise RCSExcNotFound(entity_id=str(event_id))
    await app.state.engine.delete(event)
    await Event.clean(event_id)
    # return event
