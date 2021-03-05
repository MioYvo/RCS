import json
import logging

from aio_pika import Connection, Message
from pamqp.specification import Basic
from schema import Schema, SchemaError, Optional as SchemaOptional

from Access.settings import AccessExchangeName
from utils.encoder import MyEncoder
from utils.gtz import Dt
from utils.web import BaseRequestHandler


async def publisher(conn: Connection,
                    message: dict,
                    exchange_name: str,
                    routing_key: str = "",
                    **message_kwargs,):
    channel = await conn.channel()
    try:
        exchange = await channel.get_exchange(exchange_name)
        rst = await exchange.publish(
            message=Message(
                body=bytes(json.dumps(message, cls=MyEncoder), 'utf-8'),
                **message_kwargs
            ),
            routing_key=routing_key
        )
    except Exception as e:
        logging.error(e)
        logging.error(
            f"Published Failed exchange:{exchange_name} routing_key:{routing_key} : {message['type']} -> {message}")
        return False, e, message
    else:
        if isinstance(rst, Basic.Ack):
            # normal got ack
            return True, rst, message
        else:
            logging.error(
                f"Published&Delivered exchange:{exchange_name} routing_key:{routing_key} :"
                f" {rst} -> {message}")
            return False, rst, message
    finally:
        await channel.close()


class APIError(Exception):
    pass


class AccessHandler(BaseRequestHandler):
    async def post(self):
        data = self.schema_get()
        tf, rst, sent_msg = await publisher(
            conn=self.application.amqp_connection,
            message=data, exchange_name=AccessExchangeName,
            routing_key="event", timestamp=Dt.now_ts(),
        )

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
