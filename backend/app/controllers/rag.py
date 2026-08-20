from app.core.error import NotFoundError
from app.models.rag import Repository, RepoStatus
from app.schemas.rag import ChatRequest, RepositoryCreate
from app.services.rag import RAGService
from app.tasks.rag import index_repository_task


class RAGController:
    def __init__(self) -> None:
        self._ragService = RAGService()

    async def create_repository(self, data: RepositoryCreate):
        repository = Repository(github_url=data.github_url, total_chunks=0, name="repo")
        repo = await self._ragService.create(repository)
        if not repo.id:
            raise NotFoundError("Repository id not found")

        repo_id = str(repo.id)
        task = index_repository_task.delay(
            repo_id,
            repository.github_url,
        )
        await self._ragService.update_celery_task_id(repo.id, task.id)
        return {
            "repository_id": repo_id,
            "task_id": task.id,
            "status": "queued",
        }

    async def index_repository(self, id: str):
        repo = await self._ragService.find_by_id(id)
        if not repo.id:
            raise NotFoundError("Repository id not found")
        repo_id = str(repo.id)
        task = index_repository_task.delay(
            repo_id,
            repo.github_url,
        )
        await self._ragService.update_celery_task_id(
            repo.id, task.id, RepoStatus.QUEUED
        )
        return {
            "repository_id": repo_id,
            "task_id": task.id,
            "status": "queued",
        }

    async def repository_status(self, id: str):
        repo = await self._ragService.find_by_id_meta(id)
        return repo

    async def chat(self, chat: ChatRequest):
        repo = await self._ragService.chat(chat)
        return repo


controller = RAGController()

__all__ = ["controller"]
