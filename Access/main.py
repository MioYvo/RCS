import logging
import sys
from pathlib import Path

import uvicorn
from loguru import logger
from starlette.middleware.cors import CORSMiddleware

from config.clients import consuls

sys.path.insert(0, str(Path().absolute().parent))

from config import PROJECT_NAME, LOG_FILE_PATH, LOG_FILENAME, LOG_FILE_ROTATION, LOG_FILE_RETENTION, \
    CONSUL_SERVICE_NAME, CONSUL_SERVICE_ID, TRAEFIK_HOST, TRAEFIK_HTTP_PORT
from utils.fastapi_app import app
from utils.logger import format_record, InterceptHandler
logging.getLogger().handlers = [InterceptHandler()]
logger.configure(
    handlers=[{"sink": sys.stdout, "level": logging.INFO, "format": format_record}]
)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
# logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
# logging.getLogger("uvicorn").handlers = [InterceptHandler()]
logging.getLogger("uvicorn.asgi").handlers = [InterceptHandler()]
logger.add(Path(LOG_FILE_PATH) / LOG_FILENAME, retention=LOG_FILE_RETENTION, rotation=LOG_FILE_ROTATION)


from Access.api.api_v1.api import api_router
app.docs_url = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


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
    logger.info(f"{PROJECT_NAME} starting")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, access_log=True)
