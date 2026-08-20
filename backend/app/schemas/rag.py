from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.models.rag import RepoStatus


class RepositoryCreate(BaseModel):
    github_url: str


class ChatRequest(BaseModel):
    repository_id: str
    question: str
    top_k: int = Field(default=6, ge=1, le=20)

class RepositoryMeta(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    status: RepoStatus
    total_chunks: int
    error: str | None = None

    class Config:
        populate_by_name = True
