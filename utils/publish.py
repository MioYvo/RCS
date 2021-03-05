# coding=utf-8
# __author__ = 'Mio'
import json

from aio_pika import Message, exceptions, Connection
from pamqp.specification import Basic
from tornado.log import app_log as logging

from utils.encoder import MyEncoder


async def publish(message, amqp_connection: Connection, routing_key="", exchange_name='default_exchange'):
    assert routing_key
    channel = await amqp_connection.channel()
    try:
        if exchange_name == 'default_exchange':
            exchange = channel.default_exchange
        else:
            exchange = await channel.get_exchange(exchange_name)

        rst = await exchange.publish(
            message=Message(body=bytes(json.dumps(message, cls=MyEncoder), 'utf-8')),
            routing_key=routing_key
        )
    except exceptions.ChannelClosed as e:
        # get_exchange failed
        logging.error(f"[Pub Failed] exchange not found: {exchange_name}. {e}. {routing_key} : {message}")
        return False, e, message
    except Exception as e:
        logging.error(e)
        logging.error(
            f"[Pub Failed] {e} {routing_key} : {message}")
        return False, e, message
    else:
        if isinstance(rst, Basic.Ack):
            logging.info(
                f"[Published&Ack Success] {routing_key} : {message}")
            return True, rst, message
        else:
            logging.error(
                f"[Published&Delivered] {routing_key} : {message}")
            return False, rst, message
    finally:
        await channel.close()
