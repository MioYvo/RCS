import logging
import sys
from pathlib import Path
from loguru import logger
sys.path.insert(0, str(Path().absolute().parent))

from RuleEngine.handler.executor import RuleExecutorConsumer
from utils.mpika import make_consumer
from config import PROJECT_NAME, RULE_EXE_QUEUE_NAME, RCSExchangeName, PRE_FETCH_COUNT, LOG_FILE_PATH, LOG_FILENAME, \
    LOG_FILE_RETENTION, LOG_FILE_ROTATION, RUN_PORT
from utils.fastapi_app import app
from utils.logger import format_record, InterceptHandler
logging.getLogger().handlers = [InterceptHandler()]
logger.configure(
    handlers=[{"sink": sys.stdout, "level": logging.INFO, "format": format_record}]
)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
logger.add(Path(LOG_FILE_PATH) / LOG_FILENAME, retention=LOG_FILE_RETENTION, rotation=LOG_FILE_ROTATION)


@app.on_event("startup")
async def startup_event():
    consumer = RuleExecutorConsumer(amqp_connection=app.state.amqp_connection)
    re_consumers, app.state.re_consumer_channels = await make_consumer(
        amqp_connection=app.state.amqp_connection,
        queue_name=RULE_EXE_QUEUE_NAME,
        exchange=RCSExchangeName,
        routing_key=consumer.routing_key,
        consume=consumer.consume,
        prefetch_count=PRE_FETCH_COUNT,
        auto_delete=True
    )


@app.on_event("shutdown")
async def shutdown_event():
    for channel in app.state.re_consumer_channels:
        if not channel.is_closed:
            logger.info(f'Channel closing: {channel}')
            await channel.close()


if __name__ == "__main__":
    import uvicorn
    logger.info(f"{PROJECT_NAME} starting")
    uvicorn.run(app, host="0.0.0.0", port=RUN_PORT)
