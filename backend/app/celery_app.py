import logging
import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
logger.info(f"Using Redis broker: {REDIS_URL}")

celery_app = Celery("repo_tasks", broker=REDIS_URL, backend=REDIS_URL)

celery_app = Celery(
    "repoRAG_worker", broker=REDIS_URL, backend=REDIS_URL, include=["app.tasks.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_pool_limit=2,
    redis_max_connections=4,
)

__all__=["celery_app"]