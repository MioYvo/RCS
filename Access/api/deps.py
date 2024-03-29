import json
import secrets
from math import ceil
from uuid import uuid4
from typing import Any

from pysmx.SM3 import hash_msg
from pydantic import BaseModel
from dataclasses import dataclass
from fastapi.responses import Response
from fastapi import Depends, HTTPException, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from utils.fastapi_app import app
from model.odm import Handler, HandlerRole
from utils.encoder import MyEncoder


class Pagination(BaseModel):
    total: int
    count: int
    per_page: int
    current_page: int
    total_pages: int


@dataclass
class Page:
    total: int
    page: int
    per_page: int
    count: int = 0

    @property
    def pages(self):
        if self.per_page == 0 or self.total is None:
            pages = 0
        else:
            pages = int(ceil(self.total / float(self.per_page)))
        return pages

    def meta_pagination(self):
        return {
            "total": self.total,
            "count": self.count,
            "per_page": self.per_page,
            "current_page": self.page,
            "total_pages": self.pages,
        }


class YvoJSONResponse(Response):
    """
    Usage: @router.delete("/event/{event_id}", status_code=200, response_class=YvoJSONResponse)
    """
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=MyEncoder
        ).encode("utf-8")


security = HTTPBearer(auto_error=True)


async def get_current_username(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Handler:
    if not credentials:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            # headers={"WWW-Authenticate": "Basic"},
        )
    handler = await app.state.engine.find_one(Handler, Handler.token == credentials.credentials)
    if not handler:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect user",
            # headers={"WWW-Authenticate": "Basic"},
        )
    return handler


async def get_current_username_admin(handler: Handler = Depends(get_current_username)) -> Handler:
    if handler.role != HandlerRole.ADMIN:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Insufficient role",
            # headers={"WWW-Authenticate": "Basic"},
        )
    return handler


@app.get("/api/users/me", tags=['User'])
def read_current_user(handler: Handler = Depends(get_current_username)):
    return {"username": handler.name, "role": handler.role.value,
            'token': handler.token, "create_at": handler.create_at}


@app.post("/api/users/login", tags=['User'])
async def login(username: str = Form(...),
                password: str = Form(..., description='must encoded with b64')):
    handler: Handler = await app.state.engine.find_one(Handler, Handler.name == username)
    if not handler:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Wrong username")

    # prevent Timing Attack
    if secrets.compare_digest(hash_msg(password), handler.encrypted_password):
        if not handler.token:
            handler.token = hash_msg(str(uuid4()))
            await app.state.engine.save(handler)

        return {"username": handler.name, "role": handler.role.value,
                'token': handler.token, "create_at": handler.create_at}
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Wrong credentials")


@app.post("/api/users/reset_password", tags=['User'])
async def reset_password(password: str = Form(..., description='must encoded with b64'),
                         handler: Handler = Depends(get_current_username)):
    handler.encrypted_password = hash_msg(password)
    handler.token = hash_msg(str(uuid4()))
    await app.state.engine.save(handler)

    return {"username": handler.name, "role": handler.role.value,
            'token': handler.token, "create_at": handler.create_at}


@app.post("/api/users/", tags=['Admin'],
          dependencies=[Depends(get_current_username_admin)],
          description='Create new user')
async def create_user(username: str = Form(...),
                      role: HandlerRole = HandlerRole.CUSTOMER_SERVICE,
                      password: str = Form(..., description='must encoded with b64')):

    new_handler = Handler(name=username, role=role, encrypted_password=hash_msg(password), token=hash_msg(str(uuid4())))
    await app.state.engine.save(new_handler)

    return {"username": new_handler.name, "role": new_handler.role.value,
            "create_at": new_handler.create_at}
