import tornado.ioloop
import uvloop
from aiocache import Cache
from aiocache.plugins import HitMissRatioPlugin
from aiocache.serializers import StringSerializer, JsonSerializer
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from redis import Redis

from DataProcessor.settings import MONGO_URI, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASS, PROJECT_NAME, MONGO_DB, \
    MONGO_COLLECTION_EVENT, MONGO_COLLECTION_RECORD

m_client: AsyncIOMotorClient = AsyncIOMotorClient(str(MONGO_URI))
m_db: AsyncIOMotorDatabase = getattr(m_client, MONGO_DB)
event_collection: AsyncIOMotorCollection = getattr(m_db, MONGO_COLLECTION_EVENT)
record_collection: AsyncIOMotorCollection = getattr(m_db, MONGO_COLLECTION_RECORD)

uvloop.install()
ioloop = tornado.ioloop.IOLoop.current()


# ------------- redis BEGIN -------------
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
    kwargs_s = '__'.join(map(lambda x: f"{x[0]}:{x[1]}", kwargs.items()))
    return f'{PROJECT_NAME}:{func.__name__}:kwargs:{kwargs_s}'


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
