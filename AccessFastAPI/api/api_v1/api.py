from fastapi import APIRouter

from AccessFastAPI.api.api_v1.endpoints import event, record, rule

api_router = APIRouter()
api_router.include_router(event.router, tags=["event"])
api_router.include_router(record.router, tags=["record"])
api_router.include_router(rule.router, tags=["rule"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
