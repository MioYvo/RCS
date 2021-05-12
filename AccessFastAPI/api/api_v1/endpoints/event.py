# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 6:57 PM
from fastapi import APIRouter, HTTPException, Query
from odmantic.field import FieldProxy
from odmantic.query import SortExpression

from model.odm import Event
from AccessFastAPI.core.app import app
from AccessFastAPI.api.deps import Page, YvoJSONResponse

router = APIRouter()


@router.post("/event/", response_model=Event)
async def create_event(event: Event):
    try:
        await app.state.engine.save(event)
    except Exception as e:
        raise HTTPException(400, str(e))
    return event


@router.get("/event/")
async def get_events(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1),
        sort: str = 'update_at',
        desc: bool = True, name: str = ""):

    sort: FieldProxy = getattr(Event, sort)
    if not sort:
        raise HTTPException(400, detail=f"sort key {sort} not found")
    sort: SortExpression = sort.desc() if desc else sort.asc()
    # skip
    skip = (page - 1) * per_page
    limit = per_page
    # build queries:
    queries = []
    if name:
        queries.append(Event.name.match(name))
    # count to calculate total_page
    total_count = await app.state.engine.count(Event, *queries)
    events = await app.state.engine.gets(Event, *queries, sort=sort, skip=skip, limit=limit,
                                         return_doc=True)
    p = Page(total=total_count, page=page, per_page=per_page, count=len(events))
    return YvoJSONResponse(
        dict(message='', error_code=0, content=events, meta=p.meta_pagination()),
    )
