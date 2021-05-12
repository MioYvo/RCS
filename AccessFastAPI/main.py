import logging
import sys
from pathlib import Path
from loguru import logger
sys.path.insert(0, str(Path().absolute().parent))

from AccessFastAPI.core.logger import InterceptHandler, format_record
from AccessFastAPI.api.api_v1.api import api_router
from AccessFastAPI.core.app import app

logging.getLogger().handlers = [InterceptHandler()]
logger.configure(
    handlers=[{"sink": sys.stdout, "level": logging.INFO, "format": format_record}]
)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
# logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
# logging.getLogger("uvicorn").handlers = [InterceptHandler()]
from starlette.middleware.cors import CORSMiddleware

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
