from typing import Annotated

from fastapi import Depends, Request, Response
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from app.controllers.auth import controller
from app.core.error import ForbiddenError, UnauthorizedError
from app.core.security import decodeAccessToken
from app.models.auth import AuthDepData, TokenType
from app.models.user import Role


async def is_authenticated(request: Request, response: Response):
    access_token: str | None = request.cookies.get("access_token")
    refresh_token: str | None = request.cookies.get("refresh_token")

    credentials_exception = UnauthorizedError(
        "Unauthorized: Could not validate credentials"
    )

    session_expired = UnauthorizedError("Session expired, please log in again")

    if access_token:
        try:
            payload = decodeAccessToken(access_token)
            if payload.type != TokenType.ACCESS:
                raise credentials_exception
            return AuthDepData(user_id=payload.sub, role=payload.role)
        except ExpiredSignatureError:
            pass
        except PyJWTError:
            raise credentials_exception

    if not refresh_token:
        raise session_expired

    token = await controller.refresh(request, response)

    token_decoded = decodeAccessToken(token.access_token)
    return AuthDepData(user_id=token_decoded.sub, role=token_decoded.role)


def is_authenticated_rbca(role: list[Role]):
    async def role_checker(
        sub: Annotated[AuthDepData, Depends(is_authenticated)],
    ):
        if sub and sub.role not in role:
            raise ForbiddenError("Not enough permissions")
        return sub

    return role_checker


__all__ = ["is_authenticated", "is_authenticated_rbca"]
