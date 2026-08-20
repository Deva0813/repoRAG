from enum import Enum

from app.models.common import BaseDocumentWithSoftDelete


class RepoStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    COMPLETED = "completed"
    SCANNING = "scanning"
    EMBEDDING = "embedding"
    FAILED = "failed"
    QUEUED = "queued"


class Repository(BaseDocumentWithSoftDelete):
    github_url: str
    name: str
    status: RepoStatus = RepoStatus.PENDING
    total_chunks: int = 0
    celery_task_id: str | None = None
    error: str | None = None

    class Settings:
        name = "repos"


class CodeChunk(BaseDocumentWithSoftDelete):
    repository_id: str
    content: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    embedding: list[float]

    class Settings:
        name = "code_chunks"
