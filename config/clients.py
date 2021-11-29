from asyncio import AbstractEventLoop, BaseEventLoop, get_event_loop
from typing import Union

# import tornado.ioloop
import httpx
import uvloop
from aiocache import Cache
from aiocache.plugins import HitMissRatioPlugin
from aiocache.serializers import StringSerializer, JsonSerializer, PickleSerializer
from motor.core import AgnosticCollection, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from redis import Redis

from config import MONGO_URI, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASS, MONGO_DB, \
    MONGO_COLLECTION_EVENT, MONGO_COLLECTION_RECORD, MONGO_COLLECTION_RULE, CACHE_NAMESPACE, CONSUL_CONN
from config.parser import parse_consul_config, key_builder_only_kwargs
from utils.logger import Logger
from utils.u_consul import Consul

uvloop.install()
ioloop = get_event_loop()
# noinspection PyUnresolvedReferences
# io_loop: Union[AbstractEventLoop, BaseEventLoop] = ioloop.asyncio_loop
io_loop: Union[AbstractEventLoop, BaseEventLoop] = ioloop

m_client: AsyncIOMotorClient = AsyncIOMotorClient(
    str(MONGO_URI), io_loop=io_loop,
    retryWrites=False   # For Amazon DocumentDB
)
m_db: AgnosticDatabase = getattr(m_client, MONGO_DB)
event_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_EVENT)
record_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_RECORD)
rule_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_RULE)

logger = Logger(name="RCS")


# ------------- redis BEGIN -------------
redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASS)
redis_cache_only_kwargs = dict(
    cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
    db=REDIS_DB, password=REDIS_PASS,
    namespace=CACHE_NAMESPACE,
    key_builder=key_builder_only_kwargs,
    plugins=[HitMissRatioPlugin()]
)
redis_cache_no_self = dict(
    cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
    db=REDIS_DB, password=REDIS_PASS,
    namespace=CACHE_NAMESPACE,
    # key_builder=key_builder_only_kwargs,
    noself=True,
    plugins=[HitMissRatioPlugin()]
)
# print(redis_cache_only_kwargs)
# aio redis, wait aioredis 2.0
# a_redis_pool = aioredis.create_pool(address=f"redis://{REDIS_HOST}:{REDIS_PORT}",
#                                     db=REDIS_DB, password=REDIS_PASS, maxsize=20)
# a_redis = aioredis.Redis(a_redis_pool, )
# cache
string_serializer = StringSerializer()
json_serializer = JsonSerializer()
pickle_serializer = PickleSerializer()
cache = Cache(
    cache_class=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
    # namespace=PROJECT_NAME,
    db=REDIS_DB, password=REDIS_PASS, serializer=pickle_serializer
)


# http client
limits = httpx.Limits(max_connections=200, max_keepalive_connections=40)
timeout = httpx.Timeout(10.0)
httpx_client = httpx.AsyncClient(limits=limits, timeout=timeout)


# Consul
consuls_config = parse_consul_config(CONSUL_CONN)       # "Project#Token@Host:Port Project2#Token2@Host2:Port2"
consuls = {k: Consul(loop=io_loop, client=httpx_client, **v) for k, v in consuls_config.items()}
