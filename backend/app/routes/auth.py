from fastapi import Request, Response
from fastapi.routing import APIRouter

from app.controllers.auth import controller
from app.models.auth import Token
from app.schemas.auth import LoginData, LoginResponse, RegisterData, RegisterResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(data: RegisterData, response: Response):
    return await controller.register(data, response)


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginData, response: Response):
    return await controller.login(data, response)


@router.post("/refresh", response_model=Token)
async def refresh(request: Request, response: Response):
    return await controller.refresh(request, response)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    await controller.logout(request, response)


# @router.get("/me")
# async def me(user_id: str = Depends(get_current_user_id)):
#     return {"user_id": user_id}
