from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter

from app.controllers.user import controller
from app.dependencies.auth import is_authenticated, is_authenticated_rbca
from app.models.auth import AuthDepData
from app.models.user import Role
from app.schemas.common import ListResponsePaginated
from app.schemas.user import UserResponse, UserUpdateData

router = APIRouter(prefix="/user", tags=["user"])

UserAuthDep = Annotated[
    AuthDepData,
    Depends(is_authenticated_rbca([Role.USER])),
]

AdminAuthDep = Annotated[
    AuthDepData,
    Depends(is_authenticated_rbca([Role.ADMIN])),
]

AdminOrSuperAdminAuthDep = Annotated[
    AuthDepData,
    Depends(is_authenticated_rbca([Role.ADMIN, Role.SUPER_ADMIN])),
]

AuthDep = Annotated[AuthDepData, Depends(is_authenticated)]


@router.get(
    "/id/{id}",
    response_model=UserResponse,
)
async def get_user_by_id(id: str, _: AdminOrSuperAdminAuthDep):
    return await controller.findById(id)


@router.get("/all", response_model=ListResponsePaginated[UserResponse])
async def get_all_users(
    _: AdminOrSuperAdminAuthDep, page: int = 1, limit: int = 10, s: str | None = None
):
    return await controller.findAll(page, limit, s)


@router.patch("/id/{id}", response_model=UserResponse)
async def update_user_by_id(_: AdminOrSuperAdminAuthDep, id: str, data: UserUpdateData):
    return await controller.updateById(id, data)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_my_user_data(sub: AuthDep):
    return await controller.findById(sub.user_id)


@router.patch(
    "/me",
    response_model=UserResponse,
)
async def update_my_user_data(sub: AuthDep, data: UserUpdateData):
    return await controller.updateById(sub.user_id, data)
