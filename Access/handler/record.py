from abc import ABC

from schema import Schema, SchemaError, Optional as SchemaOptional

from Access.settings import AccessExchangeName, EVENT_ROUTING_KEY
from utils.amqp_publisher import publisher
from utils.gtz import Dt
from utils.web import BaseRequestHandler


class AccessHandler(BaseRequestHandler, ABC):
    async def post(self):
        data = self.schema_get()
        tf, rst, sent_msg = await publisher(
            conn=self.application.amqp_connection,
            message=data, exchange_name=AccessExchangeName,
            routing_key=EVENT_ROUTING_KEY, timestamp=Dt.now_ts(),
        )
        if tf:
            self.write_response(content=dict(rst))
        else:
            self.write_parse_args_failed_response(content=dict(rst))

    def schema_get(self):
        try:
            _data = Schema({
                "event_id": int,
                SchemaOptional("event_ts", default=int(Dt.now_ts() * 1000)): int,
                "event_params": dict    # dynamic load from db and cached
            }).validate(self.get_body_args())
        except SchemaError as e:
            raise self.write_parse_args_failed_response(str(e))
        else:
            return _data
