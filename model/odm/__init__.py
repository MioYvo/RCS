# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 6:27 PM
import datetime
from typing import List, Optional

from loguru import logger
from odmantic import Model, ObjectId, Reference, Field
from pydantic import validator

from utils.exceptions import RCSExcErrArg
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

    @classmethod
    def validate_schema(cls, schema: dict, json: dict):
        try:
            EventSchema.validate(schema, json)
        except Exception as e:
            return False, str(e)
        else:
            return True, ''

    async def fetch_strategy_latest_record(self, metric: str):
        from utils.fastapi_app import app
        # noinspection PyUnresolvedReferences
        records = await app.state.engine.gets(Record, Record.event == self.id,
                                              sort=Record.create_at.desc(), limit=1)
        # record = await Record.get_latest_by_event_id(event_id=self.id)
        if records:
            record = records[0]
        else:
            raise Exception('record not found')
        if record.event_data.get(metric) is not None:
            return record.event_data[metric]
        else:
            raise Exception('metric func not implemented')


class Record(Model):
    event: Event = Reference()
    event_data: dict
    event_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)


class Rule(Model):
    rule: list
    name: str = Field(max_length=25)
    update_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    create_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
