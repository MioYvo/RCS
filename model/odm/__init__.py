# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 6:27 PM
import datetime
from typing import List, Optional

from loguru import logger
from odmantic import Model, ObjectId, Reference, Field
from pydantic import validator

from AccessFastAPI.core.exceptions import RCSExcErrArg
from utils.event_schema import EventSchema


# class Schema(EmbeddedModel):
#     user_id: Optional[dict]
#     dt: Optional[dict]
#     ts: Optional[dict]
#     amount: Optional[dict]

class Event(Model):
    rcs_schema: dict
    name: str = Field(max_length=25)
    rules: List[ObjectId] = Field(default_factory=list)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)

    # noinspection PyMethodParameters
    @validator("rcs_schema")
    def check_rcs_schema(cls, v) -> dict:
        try:
            EventSchema.parse(v)
        except Exception as e:
            logger.debug(e)
            raise RCSExcErrArg(content="EventSchema parse failed")
        return v


class Record(Model):
    event_id: Event = Reference()
    event: dict
    event_ts: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)


class Rule(Model):
    rule: list
    name: str = Field(max_length=25)
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
