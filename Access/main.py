import logging
import sys
from pathlib import Path
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
sys.path.insert(0, str(Path().absolute().parent))

from config import PROJECT_NAME, LOG_FILE_PATH, LOG_FILENAME, LOG_FILE_ROTATION, LOG_FILE_RETENTION
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

if __name__ == "__main__":
    import uvicorn
    logger.info(f"{PROJECT_NAME} starting")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, access_log=True)
