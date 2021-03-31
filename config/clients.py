from asyncio import AbstractEventLoop, BaseEventLoop
from typing import Union

import tornado.ioloop
import uvloop
from aiocache import Cache
from aiocache.plugins import HitMissRatioPlugin
from aiocache.serializers import StringSerializer, JsonSerializer, PickleSerializer
from motor.core import AgnosticCollection, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from redis import Redis

from config import MONGO_URI, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASS, PROJECT_NAME, MONGO_DB, \
    MONGO_COLLECTION_EVENT, MONGO_COLLECTION_RECORD, MONGO_COLLECTION_RULE
from utils.logger import Logger

uvloop.install()
ioloop = tornado.ioloop.IOLoop.current()
io_loop: Union[AbstractEventLoop, BaseEventLoop] = ioloop.asyncio_loop

m_client: AsyncIOMotorClient = AsyncIOMotorClient(str(MONGO_URI), io_loop=io_loop)
m_db: AgnosticDatabase = getattr(m_client, MONGO_DB)
event_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_EVENT)
record_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_RECORD)
rule_collection: AgnosticCollection = getattr(m_db, MONGO_COLLECTION_RULE)

logger = Logger(name="RCS")


# ------------- redis BEGIN -------------
# noinspection PyUnusedLocal
def key_builder_only_kwargs(func, *ignore, **kwargs):
    # python 3.8 support kwargs only by `def func(a, *, kw_only)`
    # but not support `def func(a, *, **kw_only)`
    # why kwargs only?
    # because if func is a class method, like
    #
    # class SomeClass:
    #     def func(self, a): ...,
    #
    # if you call func by args not kwargs, like: `SomeClass().func(a)`
    # *ignore will be [self, a], *self* is different in every call
    # so this key_builder require a kwargs only func
    extra = ""
    if ignore:
        if isinstance(ignore[0], type):
            extra += f"{ignore[0].__name__}"
        else:
            extra = PROJECT_NAME
    kwargs_s = '__'.join(map(lambda x: f"{x[0]}:{x[1]}", kwargs.items()))
    return f'{extra}:{func.__name__}:kwargs:{kwargs_s}'


redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASS)
redis_cache_only_kwargs = dict(
    cache=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
    db=REDIS_DB, password=REDIS_PASS,
    namespace=PROJECT_NAME,
    key_builder=key_builder_only_kwargs,
    plugins=[HitMissRatioPlugin()]
)
string_serializer = StringSerializer()
json_serializer = JsonSerializer()
pickle_serializer = PickleSerializer()
cache = Cache(
    cache_class=Cache.REDIS, endpoint=REDIS_HOST, port=REDIS_PORT,
    namespace=PROJECT_NAME, db=REDIS_DB, password=REDIS_PASS, serializer=pickle_serializer
)
