# __author__ = "Mio"
# __email__: "liurusi.101@gmail.com"
# created: 5/12/21 11:42 PM

from loguru import logger
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from AccessFastAPI.core.yvo_engine import YvoEngine
from config import PROJECT_NAME, MONGO_URI, MONGO_DB

app = FastAPI(title=PROJECT_NAME)


@app.on_event("startup")
async def startup_event():
    # mongo
    logger.info('mongo: connecting ...')
    app.state.engine = YvoEngine(AsyncIOMotorClient(str(MONGO_URI)), database=MONGO_DB)
    mongo_si = await app.state.engine.client.server_info()  # si: server_info
    logger.info(f'mongo:server_info version:{mongo_si["version"]} ok:{mongo_si["ok"]}')
    logger.info('mongo: connected')


@app.on_event("shutdown")
async def shutdown_event():
    # mongo
    logger.info('mongo: disconnecting ...')
    app.state.engine.client.close()
    logger.info('mongo: disconnected')
