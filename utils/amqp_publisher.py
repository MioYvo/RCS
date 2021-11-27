import json
import logging

from aio_pika import Connection, Message
from pamqp.specification import Basic

from utils.encoder import MyEncoder


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
