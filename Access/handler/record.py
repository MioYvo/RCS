from abc import ABC

from bson import ObjectId
from schema import Schema, SchemaError, Optional as SchemaOptional, Use

from config import AccessExchangeName, EVENT_ROUTING_KEY
from model.event import Event
from utils.amqp_publisher import publisher
from utils.gtz import Dt
from utils.web import BaseRequestHandler


class RecordHandler(BaseRequestHandler, ABC):
    async def post(self):
        data = await self.schema_get()
        tf, rst, sent_msg = await publisher(
            conn=self.application.amqp_connection,
            message=data, exchange_name=AccessExchangeName,
            routing_key=EVENT_ROUTING_KEY, timestamp=Dt.now_ts(),
        )
        if tf:
            self.write_response(content=dict(rst))
        else:
            self.write_parse_args_failed_response(content=dict(rst))

    async def schema_get(self):
        try:
            _data = Schema({
                "event_id": Use(ObjectId),
                SchemaOptional("event_ts", default=int(Dt.now_ts() * 1000)): int,
                "event": dict    # dynamic load from db and cached
            }).validate(self.get_body_args())
            # got event
            event = await Event.get_event(_id=_data['event_id'])
            if not event.exists:
                raise self.write_not_found_entity_response(content=dict(id=event.id))
            # validate event
            validate_rst, validate_info = event.validate(_data['event'])
            if not validate_rst:
                raise self.write_parse_args_failed_response(content=validate_info)
        except SchemaError as e:
            raise self.write_parse_args_failed_response(str(e))
        except Exception as e:
            raise self.write_parse_args_failed_response(str(e))
        else:
            return _data
