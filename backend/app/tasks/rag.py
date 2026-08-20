import asyncio
import time

from app.celery_app import celery_app
from app.core.db import init_db
from app.services.rag import RAGService


@celery_app.task(name="long_running_task")
def long_running_task(x: int, y: int):
    time.sleep(5)
    return x + y


@celery_app.task(name="index_repository")
def index_repository_task(repository_id: str, github_url: str):
    async def _run():
        await init_db()
        rag_service = RAGService()
        return await rag_service.run_indexing(
            repository_id=repository_id,
            github_url=github_url,
        )
    return asyncio.run(_run())
