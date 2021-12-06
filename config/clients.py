from asyncio import AbstractEventLoop, BaseEventLoop, get_event_loop
from typing import Union

# import tornado.ioloop
import httpx
import uvloop
from aiocache import Cache, caches, cached
from aiocache.plugins import HitMissRatioPlugin
from motor.core import AgnosticCollection, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from redis import Redis

from config import MONGO_URI, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASS, MONGO_DB, \
    MONGO_COLLECTION_EVENT, MONGO_COLLECTION_RECORD, MONGO_COLLECTION_RULE, CACHE_NAMESPACE, CONSUL_CONN, SCHEMA_TTL
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
)
m_db: AgnosticDatabase = getattr(m_client, MONGO_DB)
event_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_EVENT)
record_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_RECORD)
rule_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_RULE)

logger = Logger(name="RCS")


# ------------- redis BEGIN -------------
redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASS)
redis_cache_conf = dict(
    cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
    db=REDIS_DB, password=REDIS_PASS,
    namespace=CACHE_NAMESPACE,
    plugins=[HitMissRatioPlugin()]
)
redis_cache_no_self_conf = dict(
    cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
    db=REDIS_DB, password=REDIS_PASS,
    namespace=CACHE_NAMESPACE,
    noself=True,    # bool if you are decorating a class function
    plugins=[HitMissRatioPlugin()]
)
redis_cache_only_kwargs_conf = dict(
    cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
    db=REDIS_DB, password=REDIS_PASS,
    namespace=CACHE_NAMESPACE,
    key_builder=key_builder_only_kwargs,
    plugins=[HitMissRatioPlugin()]
)
# redis_cache = Cache(**redis_cache_conf)
# redis_cache_only_kwargs = Cache(**redis_cache_only_kwargs_conf)
# redis_cache_no_self = Cache(**redis_cache_no_self_conf)

caches.set_config({
    'default': dict(
        cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
        db=REDIS_DB, password=REDIS_PASS,
        namespace=CACHE_NAMESPACE,
        plugins=[
            {'class': "aiocache.plugins.HitMissRatioPlugin"},
            {'class': "aiocache.plugins.TimingPlugin"}
        ],
        serializer={'class': "utils.encoder.JsonSerializer"},
    ),
    'redis_cache_no_self_conf': dict(
        cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
        db=REDIS_DB, password=REDIS_PASS,
        namespace=CACHE_NAMESPACE,
        noself=True,    # bool if you are decorating a class function
        plugins=[
            {'class': "aiocache.plugins.HitMissRatioPlugin"},
            {'class': "aiocache.plugins.TimingPlugin"}
        ],
        serializer={'class': "utils.encoder.JsonSerializer"},
    ),
    'redis_cache_only_kwargs': dict(
        cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
        db=REDIS_DB, password=REDIS_PASS,
        namespace=CACHE_NAMESPACE,
        key_builder=key_builder_only_kwargs,
        plugins=[
            {'class': "aiocache.plugins.HitMissRatioPlugin"},
            {'class': "aiocache.plugins.TimingPlugin"}
        ],
        serializer={'class': "utils.encoder.JsonSerializer"},
    ),
})


def key_builder(_, *__, **kwargs):
    # DPC: Document Primary key Cache
    return f"DPC:{kwargs['model'].__name__}:{kwargs['primary_key']}"


cached_instance = cached(ttl=SCHEMA_TTL, alias='default', noself=True, key_builder=key_builder)

# print(redis_cache_only_kwargs)
# aio redis, wait aioredis 2.0
# a_redis_pool = aioredis.create_pool(address=f"redis://{REDIS_HOST}:{REDIS_PORT}",
#                                     db=REDIS_DB, password=REDIS_PASS, maxsize=20)
# a_redis = aioredis.Redis(a_redis_pool, )
# cache
# string_serializer = StringSerializer()
# json_serializer = JsonSerializer()
# pickle_serializer = PickleSerializer()


# http client
limits = httpx.Limits(max_connections=200, max_keepalive_connections=40)
timeout = httpx.Timeout(10.0)
httpx_client = httpx.AsyncClient(limits=limits, timeout=timeout)


# Consul
consuls_config = parse_consul_config(CONSUL_CONN)       # "Project#Token@Host:Port Project2#Token2@Host2:Port2"
consuls = {k: Consul(loop=io_loop, client=httpx_client, **v) for k, v in consuls_config.items()}
