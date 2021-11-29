# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 11:42 PM
import base64
import os
import secrets
import socket
from uuid import uuid4

import pymongo.errors
from aio_pika import connect_robust, Connection, Channel
from aioredis import Redis, ConnectionPool
from loguru import logger
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pysmx.SM3 import hash_msg

from model.odm import Handler, HandlerRole
from utils.exceptions import RCSException
from utils.yvo_engine import YvoEngine
from config import PROJECT_NAME, MONGO_URI, MONGO_DB, PIKA_URL, RCSExchangeName, AccessExchangeType, REDIS_DB, \
    REDIS_PASS, REDIS_CONN_MAX, REDIS_HOST, REDIS_PORT, DOCS_URL, REDOC_URL, OPENAPI_URL, ENABLE_DOC, \
    CREATE_INDEX
from utils.error_code import ERR_DB_OPERATE_FAILED

if not ENABLE_DOC:
    DOCS_URL, REDOC_URL, OPENAPI_URL = (None, ) * 3

app = FastAPI(title=PROJECT_NAME, docs_url=DOCS_URL, redoc_url=REDOC_URL, openapi_url=OPENAPI_URL, version="0.0.1")


# noinspection PyUnusedLocal
@app.exception_handler(RCSException)
async def unicorn_exception_handler(request: Request, exc: RCSException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.message), "error_code": str(exc.error_code), "content": str(exc.content)},
    )


# noinspection PyUnusedLocal
@app.exception_handler(Exception)
async def unicorn_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"content": str(exc), "arg": str(exc.args)},
    )


# noinspection PyUnusedLocal
@app.exception_handler(pymongo.errors.OperationFailure)
async def unicorn_exception_handler(request: Request, exc: pymongo.errors.OperationFailure):
    return JSONResponse(
        status_code=400,
        content={"message": "DBOperateFailed", "error_code": ERR_DB_OPERATE_FAILED, "content": str(exc.details)},
    )


async def make_queues(amqp_connection: Connection):
    channel: Channel = await amqp_connection.channel()
    # task_type direct exchange
    # for task_type in TYPE_ENUM:
    #     await channel.declare_queue(name=task_type, durable=True, auto_delete=False)
    # district topic exchange, one worker one queue
    await channel.declare_exchange(RCSExchangeName, type=AccessExchangeType, durable=True)
    await channel.close()


async def startup_rabbit():
    logger.info('rabbitMQ: connecting ...')
    app.state.amqp_connection = await connect_robust(
        url=PIKA_URL,
        client_properties={
            'client_properties': {
                'connection_name': f"{PROJECT_NAME}-{socket.gethostname()}-{os.getpid()}"
            }
        }
    )
    logger.info('rabbitMQ: connected')
    logger.info('rabbitMQ: making queues ...')
    await make_queues(amqp_connection=app.state.amqp_connection)
    logger.info('rabbitMQ: queues made')


async def startup_redis():
    logger.info('redis: connecting ...')
    app.state.a_redis_pool = ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                                            password=REDIS_PASS, max_connections=REDIS_CONN_MAX)
    app.state.a_redis = Redis(connection_pool=app.state.a_redis_pool)
    logger.info('redis: connected')


async def startup_mongo():
    logger.info('mongo: connecting ...')
    # noinspection PyTypeHints
    app.state.engine: YvoEngine = YvoEngine(AsyncIOMotorClient(str(MONGO_URI)), database=MONGO_DB,
                                            a_redis_client=app.state.a_redis)
    mongo_si = await app.state.engine.client.server_info()  # si: server_info
    logger.info(f'mongo:server_info version:{mongo_si["version"]} ok:{mongo_si["ok"]}')
    logger.info('mongo: connected')
    if CREATE_INDEX:
        from model.odm import Handler, Event, Rule, Scene
        logger.info('mongo indexes: creating ... (if data exists)')
        indexes = {
            _model: _model.index_()
            for _model in [Handler, Event, Rule, Scene]
        }

        for _model, indexes in indexes.items():
            for index in indexes:
                try:
                    logger.info(f'mongo indexes: creating {+_model}:{index.document}')
                    rst = await app.state.engine.get_collection(_model).create_indexes([index])
                    logger.info(f'mongo index {rst}')
                except Exception as e:
                    logger.error(e)
        logger.info('mongo indexes: created')


async def startup_admin_user():
    logger.info('user admin: creating ...')
    redis: Redis = app.state.a_redis
    r_key = "startup::admin_user"
    if not await redis.set(r_key, '1', ex=10, nx=True):
        logger.info('user admin: duplicated startup_admin_user')
        return

    exists_admin = await app.state.engine.find_one(Handler, Handler.name == 'admin')
    if exists_admin:
        logger.info('user admin: exists')
    else:
        pwd = secrets.token_urlsafe()
        b64_pwd = base64.b64encode(pwd.encode())
        new_admin = Handler(name='admin', role=HandlerRole.ADMIN, encrypted_password=hash_msg(b64_pwd),
                            token=hash_msg(str(uuid4())))
        logger.info(f'user admin: {pwd}, b64encoded: {b64_pwd}')
        await app.state.engine.save(new_admin)

    # await redis.delete(key=r_key)


@app.on_event("startup")
async def startup_event():
    # RabbitMQ
    await startup_rabbit()
    # Redis
    await startup_redis()
    # MongoDB
    await startup_mongo()
    # User admin
    await startup_admin_user()


@app.on_event("shutdown")
async def shutdown_event():
    # mongo
    logger.info('mongo: disconnecting ...')
    app.state.engine.client.close()
    logger.info('mongo: disconnected')

    # rabbitMQ
    logger.info('rabbitMQ: disconnecting ...')
    await app.state.amqp_connection.close()
    logger.info('rabbitMQ: disconnected')

    # redis
    logger.info('redis: disconnecting ...')
    await app.state.a_redis_pool.disconnect()
    # await app.state.a_redis.wait_closed()
    logger.info('redis: disconnected')
