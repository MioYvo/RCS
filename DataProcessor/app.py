# coding=utf-8
# __author__ = 'Mio'
import os
from pathlib import Path
from typing import List

import tornado.web
import tornado.ioloop
from aio_pika.queue import ConsumerTag
from motor.motor_asyncio import AsyncIOMotorClient
from aio_pika import connect_robust, Channel, Connection
from tornado.options import define, options, parse_command_line

from config.clients import m_client, m_db, ioloop
from DataProcessor.urls import urls
from DataProcessor.processer.access import AccessConsumer
from utils.mpika import make_consumer
from config import (
    PROJECT_NAME, PIKA_URL, AccessExchangeType, AccessExchangeName,
    MONGO_URI, PRE_FETCH_COUNT, RUN_PORT, QUEUE_NAME)

define("port", default=RUN_PORT, help=f"{PROJECT_NAME} run on the given port", type=int)
define("debug", default=False, help="run in debug mode", type=bool)
parse_command_line()


async def make_queues(amqp_connection: Connection):
    channel: Channel = await amqp_connection.channel()
    # task_type direct exchange
    # for task_type in TYPE_ENUM:
    #     await channel.declare_queue(name=task_type, durable=True, auto_delete=False)
    # district topic exchange, one worker one queue
    await channel.declare_exchange(AccessExchangeName, type=AccessExchangeType, durable=True)
    await channel.close()


async def make_app():
    if not m_client.list_database_names():
        raise Exception(f"db connect failed or no db exists: {MONGO_URI}")
    amqp_connection = await connect_robust(
        url=PIKA_URL,
        client_properties={'client_properties': {'connection_name': f"{PROJECT_NAME}-{os.getpid()}"}})
    consumer = AccessConsumer(amqp_connection=amqp_connection)
    data_processor_consumers: List[ConsumerTag] = await make_consumer(
        amqp_connection=amqp_connection,
        queue_name=QUEUE_NAME,
        exchange=AccessExchangeName,
        routing_key=consumer.routing_key,
        consume=consumer.consume,
        prefetch_count=PRE_FETCH_COUNT,
        auto_delete=True
    )

    # a_redis: RedisConnection = await aioredis.create_redis_pool(
    #     (REDIS_HOST, REDIS_PORT),
    #     minsize=10,
    #     maxsize=50,
    #     encoding='utf-8'
    # )

    return MatildaApp(
        m_db=m_db,
        m_client=m_client,
        amqp_connection=amqp_connection,
        consumers=data_processor_consumers,
    )


class MatildaApp(tornado.web.Application):
    def __init__(
            self,
            m_db,
            m_client: AsyncIOMotorClient,
            amqp_connection: Connection,
            consumers: List[ConsumerTag],
            a_redis=None,
    ):
        super(MatildaApp, self).__init__(
            handlers=urls,
            cookie_secret="Vhp1qJHkFnbP4OqssGMgVYkpu4d7tNwh",
            xsrf_cookies=False,
            login_url="/login",
            # template_path="gaffer/doc/",
            static_path=Path().absolute().parent / 'doc',
            static_url_prefix="/doc/",
            debug=options.debug,
            autoreload=options.debug,
            serve_traceback=options.debug,
        )
        self.pool = None
        self.m_client: AsyncIOMotorClient = m_client
        self.m_db = m_db
        self.live_worker = {}
        self.amqp_connection = amqp_connection
        self.consumers = consumers
        self.a_redis = a_redis


app: MatildaApp = ioloop.asyncio_loop.run_until_complete(make_app())
