import logging
import sys
from pathlib import Path

import uvicorn
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
sys.path.insert(0, str(Path().absolute().parent))

from config import PROJECT_NAME, LOG_FILE_PATH, LOG_FILENAME, LOG_FILE_ROTATION, LOG_FILE_RETENTION, \
    CONSUL_SERVICE_NAME, CONSUL_SERVICE_ID, TRAEFIK_HOST, TRAEFIK_HTTP_PORT, LOG_LEVEL
from config.clients import consuls
from utils.fastapi_app import app
from utils.logger import format_record, InterceptHandler


def filter_out_health_check(record) -> bool:
    return "api/health" not in record['message']


logging.getLogger().handlers = [InterceptHandler()]
logger.configure(
    handlers=[{"sink": sys.stdout, "level": getattr(logging, LOG_LEVEL),
               "format": format_record, "filter": filter_out_health_check}]
)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
# logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
# logging.getLogger("uvicorn").handlers = [InterceptHandler()]
logging.getLogger("uvicorn.asgi").handlers = [InterceptHandler()]

logger.add(Path(LOG_FILE_PATH) / LOG_FILENAME, level=getattr(logging, LOG_LEVEL), retention=LOG_FILE_RETENTION, rotation=LOG_FILE_ROTATION,
           filter=filter_out_health_check)

from Access.api.api_v1.api import api_router
from Access.api.health import router as health_router
app.docs_url = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api", tags=["health"])


async def init_consul():
    for proj, _consul in consuls.items():
        logger.info(f'consul:registering:{proj}:{_consul.http.host}')
        await _consul.register(name=CONSUL_SERVICE_NAME, service_id=CONSUL_SERVICE_ID,
                               address=TRAEFIK_HOST, port=TRAEFIK_HTTP_PORT)


async def exit_consul():
    for proj, _consul in consuls.items():
        logger.info(f'consul:deregister:{proj}:{_consul.http.host}')
        await _consul.agent.service.deregister(service_id=CONSUL_SERVICE_ID, token=_consul.token)


@app.on_event("startup")
async def startup_event():
    # Consul
    await init_consul()


@app.on_event("shutdown")
async def shutdown_event():
    # consul
    await exit_consul()
    logger.info('Deregister consul service')


if __name__ == "__main__":
    # from pymongo import monitoring
    # class CommandLogger(monitoring.CommandListener):
    #
    #     def started(self, event):
    #         logger.info("Command {0.command_name} with request id "
    #                      "{0.request_id} started on server "
    #                      "{0.connection_id} {0.command}".format(event))
    #
    #     def succeeded(self, event):
    #         logger.info("Command {0.command_name} with request id "
    #                      "{0.request_id} on server {0.connection_id} "
    #                      "succeeded in {0.duration_micros} "
    #                      "microseconds".format(event))
    #
    #     def failed(self, event):
    #         logger.info("Command {0.command_name} with request id "
    #                      "{0.request_id} on server {0.connection_id} "
    #                      "failed in {0.duration_micros} "
    #                      "microseconds".format(event))
    #
    #
    # monitoring.register(CommandLogger())
    logger.info(f"{PROJECT_NAME} starting")
    # must be 80, same as Dockerfile
    uvicorn.run("main:app", host="0.0.0.0", port=8080, access_log=True)
