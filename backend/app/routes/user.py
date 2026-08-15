from fastapi.routing import APIRouter

from app.controllers.user import controller
from app.models.user import User
from app.schemas.common import ListResponsePaginated
from app.schemas.user import UserResponse, UserUpdateData

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/id/{id}", response_model=UserResponse)
async def get_user_by_id(id: str):
    return await controller.findById(id)


@router.get("/all", response_model=ListResponsePaginated[UserResponse])
async def get_all_users(page: int = 1, limit: int = 10, s: str | None = None):
    return await controller.findAll(page, limit, s)


@router.patch("/id/{id}", response_model=UserResponse)
async def update_user_by_id(id: str, data: UserUpdateData):
    return await controller.updateById(id, data)
