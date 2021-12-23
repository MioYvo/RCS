# coding=utf-8
# __author__ = 'Mio'
from os import getenv

from aio_pika import ExchangeType
from yarl import URL
from pytz import timezone, tzinfo

from utils.gtz import local_timezone

# Project
PROJECT_NAME = getenv("PROJECT_NAME", "DataProcessor")
SCHEMA_TTL = int(getenv('SCHEMA_TTL', 600))
CONSUL_SERVICE_CACHE_TTL = int(getenv('SCHEMA_TTL', 60))
RCSExchangeName = getenv('RCSExchangeName', 'RCS')
AccessExchangeType = ExchangeType(getenv('AccessExchangeType', 'direct'))
DATA_PROCESSOR_ROUTING_KEY = getenv('DATA_PROCESSOR_ROUTING_KEY', 'DataProcessor')
RULE_EXE_ROUTING_KEY = getenv('RULE_EXE_ROUTING_KEY', 'RuleEngineExe')
RUN_HOST = getenv("RUN_HOST", "traefik")
RUN_PORT = int(getenv("RUN_PORT", 80))   # must be 80
CACHE_NAMESPACE = getenv('CACHE_NAMESPACE', 'RCS')
DOCS_URL = getenv('DOCS_URL', '/docs')
OPENAPI_URL = getenv('OPENAPI_URL', '/openapi.json')
REDOC_URL = getenv('REDOC_URL', '/redoc')
ENABLE_DOC = bool(int(getenv('ENABLE_DOC', 0)))
CREATE_INDEX = bool(int(getenv('CREATE_INDEX', 0)))
CREATE_ADMIN = bool(int(getenv('CREATE_ADMIN', 1)))

# Traefik
TRAEFIK_HOST = getenv("TRAEFIK_HOST", "traefik")
TRAEFIK_HTTP_PORT = int(getenv("TRAEFIK_HTTP_PORT", 801))
# LOG
LOG_FILE_PATH = getenv('LOG_FILE_PATH', '/app/log/')
LOG_FILENAME = getenv('LOG_FILENAME', f"{PROJECT_NAME}.log")
LOG_FILE_RETENTION = getenv('LOG_FILE_RETENTION', '7 days')
LOG_FILE_ROTATION = getenv('LOG_FILE_ROTATION', '1 day')
LOG_LEVEL = getenv('LOG_LEVEL', 'INFO')

# DataProcessor
PRE_FETCH_COUNT = int(getenv('PRE_FETCH_COUNT', 10))
DATA_PROCESSOR_QUEUE_NAME = getenv('DATA_PROCESSOR_QUEUE_NAME', 'DataProcessor')
RULE_EXE_QUEUE_NAME = getenv('RULE_EXE_QUEUE_NAME', 'RuleEngineExe')

# MongoDB
MONGO_HOST = getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(getenv('MONGO_PORT', 27017))
MONGO_USER = getenv('MONGO_USER', 'RCSAccess')
MONGO_PASS = getenv('MONGO_PASS')
MONGO_MAXPoolSize = getenv('MONGO_maxPoolSize', 100)
MONGO_DB = getenv('MONGO_DB', 'RCSAccess')
MONGO_COLLECTION_EVENT = getenv('MONGO_COLLECTION_EVENT', 'event')
MONGO_COLLECTION_RECORD = getenv('MONGO_COLLECTION_RECORD', 'record')
MONGO_COLLECTION_RULE = getenv('MONGO_COLLECTION_RULE', 'rule')

if not MONGO_PASS:
    MONGO_PASS_FILE = getenv('MONGO_PASS_FILE')
    if MONGO_PASS_FILE:
        with open(MONGO_PASS_FILE) as f:
            MONGO_PASS = f.read().strip()
MONGO_URI = URL.build(scheme='mongodb', host=MONGO_HOST, port=MONGO_PORT, user=MONGO_USER, password=MONGO_PASS,
                      query=dict(
                          MAXPoolSize=MONGO_MAXPoolSize,
                          retryWrites='false'     # FOR amazon documentDB
                      ))


# MariaDB
MARIA_USER = getenv('MARIA_USER')
if not MARIA_USER:
    MARIA_USER_FILE = getenv('MARIA_USER_FILE')
    if MARIA_USER_FILE:
        with open(MARIA_USER_FILE) as f:
            MARIA_USER = f.read().strip()

MARIA_PASS = getenv('MARIA_PASS')
if not MARIA_PASS:
    MARIA_PASS_FILE = getenv('MARIA_PASS_FILE')
    if MARIA_PASS_FILE:
        with open(MARIA_PASS_FILE) as f:
            MARIA_PASS = f.read().strip()

MARIA_DB = getenv('MARIA_DB')
if not MARIA_DB:
    MARIA_DB_FILE = getenv('MARIA_DB_FILE')
    if MARIA_DB_FILE:
        with open(MARIA_DB_FILE) as f:
            MARIA_DB = f.read().strip()

# assert MARIA_DB and MARIA_PASS and MARIA_USER
MARIA_HOST = getenv('MARIA_HOST', 'localhost')
MARIA_PORT = int(getenv('MARIA_PORT', '3306'))
MARIA_WAIT_TIMEOUT = int(getenv('MARIA_WAIT_TIMEOUT', 500))
MARIA_TZ: tzinfo = timezone(getenv('MARIA_TZ', str(local_timezone)))
USE_UTC_OUT_FORMAT = bool(int(getenv('USE_UTC_OUT_FORMAT', 1)))
# mysql+pymysql://root:root@localhost/monitor
MARIA_URI = f'mysql+pymysql://{MARIA_USER}:{MARIA_PASS}@{MARIA_HOST}:{MARIA_PORT}/{MARIA_DB}'
MARIA_URL = URL.build(scheme='mysql+pymysql', user=MARIA_USER, password=MARIA_PASS,
                      host=MARIA_HOST, port=MARIA_PORT, path=f'/{MARIA_DB}')
MARIA_PRE_PING = bool(int(getenv('MARIA_PRE_PING', 0)))

# # apscheduler
# assert SCHEDULER_STORE_URL

# Redis
REDIS_HOST = getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(getenv('REDIS_PORT', 6379))
REDIS_DB = int(getenv('REDIS_DB', 1))
REDIS_PASS = getenv('REDIS_PASS', None)
REDIS_CONN_MAX = int(getenv('REDIS_CONN_MAX', 5))
assert REDIS_HOST
if not REDIS_PASS:
    REDIS_PASS_FILE = getenv('REDIS_PASS_FILE')
    if REDIS_PASS_FILE:
        with open(REDIS_PASS_FILE) as f:
            REDIS_PASS = f.read().strip()
            if not REDIS_PASS:
                REDIS_PASS = None


# pika
PIKA_USER = getenv('PIKA_USER', 'RCSAccess')
PIKA_HOST = getenv('PIKA_HOST', '127.0.0.1')
PIKA_PORT = int(getenv('PIKA_PORT', '5672'))
PIKA_VHOST = getenv('PIKA_VHOST', '/')
PIKA_PASS = getenv('PIKA_PASS')
if not PIKA_PASS:
    PIKA_PASS_FILE = getenv('PIKA_PASS_FILE')
    if PIKA_PASS_FILE:
        with open(PIKA_PASS_FILE) as f:
            PIKA_PASS = f.read().strip()
assert PIKA_PASS

PIKA_URL = URL.build(
    scheme='amqp',
    host=PIKA_HOST,
    port=PIKA_PORT,
    user=PIKA_USER,
    password=PIKA_PASS
)
PIKA_MANAGEMENT_PORT = int(getenv('PIKA_MANAGEMENT_PORT', 15672))
# pika_api = AdminAPI(url=f'http://{PIKA_HOST}:{PIKA_MANAGEMENT_PORT}', auth=(PIKA_USER, PIKA_PASS))
# rabbit_api = Client(api_url=f'{PIKA_HOST}:{PIKA_MANAGEMENT_PORT}', user=PIKA_USER, passwd=PIKA_PASS)

# HTTP client
# AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", defaults=dict(
max_clients = int(getenv('http_clients_max_clients', 50))
max_body_size = int(getenv('http_clients_max_body_size_bytes', 204800))  # 200 KB
max_header_size = int(getenv('http_clients_max_header_size_bytes', 10240))  # 10 KB
user_agent = getenv('http_clients_default_user_agent',
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:73.0) Gecko/20100101 Firefox/73.0")

# AsyncHTTPClient.configure(None, defaults=dict(
# AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", defaults=dict(
#     max_clients=max_clients,
#     max_body_size=max_body_size,  # 200 KB
#     max_header_size=max_header_size,  # 10 KB
#     user_agent=user_agent
# ))
# a_http_client = AsyncHTTPClient()

# Consul    "Token@Host:Port Token2@Host2:Port2"
CONSUL_CONN = getenv('CONSUL_CONN', '')
# # self consul config
CONSUL_SERVICE_NAME = getenv('CONSUL_SERVICE_NAME', 'rcs')
CONSUL_SERVICE_ID = getenv('CONSUL_SERVICE_ID', 'rcs_1')

# Rule Engine
RULE_ENGINE_USER_DATA_FORMAT = getenv('SPECIAL_USER_DATA_FORMAT', '<<USER_DATA>>')

callback_service_config = {
    "VDEX": {"service_name": "vdex_dapp_phpservice"},
    "PAYDEX": {"service_name": "paydex_dapp_phpservice"},
    "lland_dapp_phpservice_dev": {
        # 开发环境
        # php api服务: http://10.75.0.29:80
        # php consul: http://10.75.0.29:8500
        # project/consul service_name: lland_dapp_phpservice_dev
        "service_name": "lland_dapp_phpservice_dev",
        "punish_notice_uri": "/lland/box/v1/risk/notice"
    },
    "lland_dapp_phpservice": {
        # 测试/正式环境
        # php api服务: http://10.75.0.61:80
        # php consul: http://10.75.0.61:8500
        # project/consul service_name: lland_dapp_phpservice
        "service_name": "lland_dapp_phpservice",
        "punish_notice_uri": "/lland/box/v1/risk/notice"
    },
    "lland_dapp_phpservice_pre": {
        # 灰度环境
        # php api服务: 待定
        # php consul: 待定
        # project/consul service_name: lland_dapp_phpservice_pre
        "service_name": "lland_dapp_phpservice_pre",
        "punish_notice_uri": "/lland/box/v1/risk/notice"
    },
}

