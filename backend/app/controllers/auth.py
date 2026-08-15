from fastapi import Request, Response

from app.core.config import settings
from app.core.error import UnauthorizedError
from app.models.auth import Token
from app.schemas.auth import LoginData, LoginResponse, RegisterData, RegisterResponse
from app.services.auth import AuthService

REFRESH_COOKIE_NAME = "refresh_token"
ACCESS_COOKIE_NAME = "access_token"


class AuthController:
    def __init__(self) -> None:
        self._authService = AuthService()

    async def register(
        self, data: RegisterData, response: Response
    ) -> RegisterResponse:
        user = await self._authService.register(data)
        access_token, raw_refresh, max_age = await self._authService.issue_token(
            str(user.id)
        )
        self._set_refresh_cookie(response, raw_refresh, max_age)
        self._set_access_cookie(response, access_token)

        return RegisterResponse(
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            email=user.email,
            token=Token(access_token=access_token, refresh_token=raw_refresh),
        )

    async def login(self, data: LoginData, response: Response) -> LoginResponse:
        user = await self._authService.authenticate(data)
        access_token, raw_refresh, max_age = await self._authService.issue_token(
            str(user.id),
            settings.refresh_token_expire_days_max
            if data.remember_me
            else settings.refresh_token_expire_days,
        )
        self._set_refresh_cookie(response, raw_refresh, max_age)
        self._set_access_cookie(response, access_token)
        return LoginResponse(
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            email=user.email,
            token=Token(access_token=access_token, refresh_token=raw_refresh),
        )

    async def refresh(self, request: Request, response: Response) -> Token:
        raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
        if not raw_token:
            raise UnauthorizedError("Missing refresh token")

        (
            access_token,
            new_raw_refresh,
            max_age,
        ) = await self._authService.rotate_refresh_token(raw_token)
        self._set_refresh_cookie(response, new_raw_refresh, max_age)
        self._set_access_cookie(response, access_token)
        return Token(access_token=access_token)

    async def logout(self, request: Request, response: Response) -> None:
        raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
        if raw_token:
            await self._authService.revoke_refresh_token(raw_token)
        response.delete_cookie(
            REFRESH_COOKIE_NAME,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
        )
        response.delete_cookie(
            key=ACCESS_COOKIE_NAME,
            secure=settings.cookie_secure,
            samesite="lax",
        )

    def _set_refresh_cookie(
        self, response: Response, raw_refresh: str, max_age: int
    ) -> None:
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=raw_refresh,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=max_age,
        )

    def _set_access_cookie(self, response: Response, access_token: str) -> None:
        response.set_cookie(
            key=ACCESS_COOKIE_NAME,
            value=access_token,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=settings.access_token_expire_minutes * 60,
        )


controller = AuthController()

__all__ = ["controller"]
