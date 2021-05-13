import json
from math import ceil
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel
from fastapi.responses import Response

from model.odm import Event
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
