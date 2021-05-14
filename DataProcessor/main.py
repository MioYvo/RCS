import logging
import sys
from pathlib import Path
from loguru import logger
sys.path.insert(0, str(Path().absolute().parent))

from DataProcessor.processer.access import AccessConsumer
from utils.mpika import make_consumer
from config import PROJECT_NAME, DATA_PROCESSOR_QUEUE_NAME, RCSExchangeName, PRE_FETCH_COUNT
from utils.fastapi_app import app
from utils.logger import format_record, InterceptHandler
logging.getLogger().handlers = [InterceptHandler()]
logger.configure(
    handlers=[{"sink": sys.stdout, "level": logging.INFO, "format": format_record}]
)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
# logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
# logging.getLogger("uvicorn").handlers = [InterceptHandler()]


@app.on_event("startup")
async def startup_event():
    app.state.consumer = AccessConsumer(amqp_connection=app.state.amqp_connection)
    dp_consumers, app.state.dp_consumer_channels = await make_consumer(
        amqp_connection=app.state.amqp_connection,
        queue_name=DATA_PROCESSOR_QUEUE_NAME,
        exchange=RCSExchangeName,
        routing_key=app.state.consumer.routing_key,
        consume=app.state.consumer.consume,
        prefetch_count=PRE_FETCH_COUNT,
        auto_delete=True
    )


@app.on_event("shutdown")
async def shutdown_event():
    for channel in app.state.dp_consumer_channels:
        if not channel.is_closed:
            logger.info(f'Channel closing: {channel}')
            await channel.close()


@app.on_event("shutdown")
async def shutdown_event():
    pass

if __name__ == "__main__":
    import uvicorn
    logger.info(f"{PROJECT_NAME} starting")
    uvicorn.run(app, host="0.0.0.0", port=8001)
