from fastapi import APIRouter as FastAPIRouter
from typing import Any, Callable

from Access.api.api_v1.endpoints import event, record, rule, result, scene, config


class APIRouter(FastAPIRouter):
    # def api_route(
    #     self, path: str, *, include_in_schema: bool = True, **kwargs: Any
    # ) -> Callable[[DecoratedCallable], DecoratedCallable]:
    #     if path.endswith("/"):
    #         path = path[:-1]
    #
    #     add_path = super().api_route(
    #         path, include_in_schema=include_in_schema, **kwargs
    #     )
    #
    #     alternate_path = path + "/"
    #     add_alternate_path = super().api_route(
    #         alternate_path, include_in_schema=False, **kwargs
    #     )
    #
    #     def decorator(func: DecoratedCallable) -> DecoratedCallable:
    #         add_alternate_path(func)
    #         return add_path(func)
    #
    #     return decorator

    def add_api_route(
            self, path: str, endpoint: Callable[..., Any], *,
            include_in_schema: bool = True, **kwargs: Any
            ) -> None:
        if path.endswith("/"):
            alternate_path = path[:-1]
        else:
            alternate_path = path + "/"
        super().add_api_route(
            alternate_path, endpoint, include_in_schema=False, **kwargs)
        return super().add_api_route(
            path, endpoint, include_in_schema=include_in_schema, **kwargs)


api_router = APIRouter()
api_router.include_router(event.router, tags=["event"])
api_router.include_router(record.router, tags=["record"])
api_router.include_router(rule.router, tags=["rule"])
api_router.include_router(result.router, tags=["result"])
api_router.include_router(scene.router, tags=["scene"])
api_router.include_router(config.router, tags=["config"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
