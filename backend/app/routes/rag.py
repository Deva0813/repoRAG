from fastapi import APIRouter

from app.controllers.rag import controller
from app.schemas.rag import ChatRequest, RepositoryCreate

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/repositories")
async def create_repository(data: RepositoryCreate):
    return await controller.create_repository(data)


@router.post("/repositories/{repository_id}/index")
async def index_repository(
    repository_id: str,
):
    return await controller.index_repository(repository_id)


@router.get("/repositories/{repository_id}/status")
async def repository_status(
    repository_id: str,
):
    return await controller.repository_status(repository_id)


@router.post("/chat")
async def chat(data: ChatRequest):
    return await controller.chat(data)
