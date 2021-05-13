# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 11:42 PM
import os

import aioredis
import pymongo.errors
from aio_pika import connect_robust, Connection, Channel
from loguru import logger
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient

from utils.exceptions import RCSException
from utils.yvo_engine import YvoEngine
from config import PROJECT_NAME, MONGO_URI, MONGO_DB, PIKA_URL, RCSExchangeName, AccessExchangeType, REDIS_DB, \
    REDIS_PASS, REDIS_CONN_MIN, REDIS_CONN_MAX, REDIS_HOST, REDIS_PORT, DOCS_URL, REDOC_URL, OPENAPI_URL, ENABLE_DOC
from utils.error_code import ERR_DB_OPERATE_FAILED

if not ENABLE_DOC:
    DOCS_URL, REDOC_URL, OPENAPI_URL = (None, ) * 3

app = FastAPI(title=PROJECT_NAME, docs_url=DOCS_URL, redoc_url=REDOC_URL, openapi_url=OPENAPI_URL)


# noinspection PyUnusedLocal
@app.exception_handler(RCSException)
async def unicorn_exception_handler(request: Request, exc: RCSException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "error_code": exc.error_code, "content": exc.content},
    )


# noinspection PyUnusedLocal
@app.exception_handler(pymongo.errors.OperationFailure)
async def unicorn_exception_handler(request: Request, exc: pymongo.errors.OperationFailure):
    return JSONResponse(
        status_code=400,
        content={"message": "DBOperateFailed", "error_code": ERR_DB_OPERATE_FAILED, "content": exc.details},
    )


async def make_queues(amqp_connection: Connection):
    channel: Channel = await amqp_connection.channel()
    # task_type direct exchange
    # for task_type in TYPE_ENUM:
    #     await channel.declare_queue(name=task_type, durable=True, auto_delete=False)
    # district topic exchange, one worker one queue
    await channel.declare_exchange(RCSExchangeName, type=AccessExchangeType, durable=True)
    await channel.close()


@app.on_event("startup")
async def startup_event():
    # rabbitMQ
    logger.info('rabbitMQ: connecting ...')
    app.state.amqp_connection = await connect_robust(
        url=PIKA_URL,
        client_properties={'client_properties': {'connection_name': f"{PROJECT_NAME}-{os.getpid()}"}})
    logger.info('rabbitMQ: connected')
    logger.info('rabbitMQ: making queues ...')
    await make_queues(amqp_connection=app.state.amqp_connection)
    logger.info('rabbitMQ: queues made')

    # redis
    logger.info('redis: connecting ...')
    app.state.a_redis = await aioredis.create_redis_pool(
        address=(REDIS_HOST, REDIS_PORT), db=REDIS_DB, password=REDIS_PASS,
        encoding='utf-8', minsize=REDIS_CONN_MIN, maxsize=REDIS_CONN_MAX
    )
    logger.info('redis: connected')

    # mongo
    logger.info('mongo: connecting ...')
    app.state.engine = YvoEngine(AsyncIOMotorClient(str(MONGO_URI)), database=MONGO_DB,
                                 a_redis_client=app.state.a_redis)
    mongo_si = await app.state.engine.client.server_info()  # si: server_info
    logger.info(f'mongo:server_info version:{mongo_si["version"]} ok:{mongo_si["ok"]}')
    logger.info('mongo: connected')


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
    app.state.a_redis.close()
    await app.state.a_redis.wait_closed()
    logger.info('redis: disconnected')
