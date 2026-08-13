from datetime import UTC, datetime, timedelta

import jwt
from beanie import PydanticObjectId
from beanie.odm.operators.update.general import Set

from app.core.error import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    createAccessToken,
    decodeAccessToken,
    generateRefreshToken,
    hash_refresh_token,
    hashPassword,
    verifyPassword,
)
from app.models.auth import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginData, RegisterData


class AuthService:
    @staticmethod
    async def register(data: RegisterData) -> User:
        existing = await User.find_one(User.email == data.email)
        if existing:
            raise ConflictError("Email already registered")

        hashed_password = hashPassword(data.password)
        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            hashed_password=hashed_password,
            phone_number=data.phone_number,
        )

        await user.insert()
        return user

    @staticmethod
    async def authenticate(data: LoginData) -> User:
        user = await User.find_one(User.email == data.email)
        if (
            (not user)
            or (not verifyPassword(data.password, user.hashed_password))
            or (user.is_deleted())
        ):
            raise NotFoundError("Email or Password is invalid")

        return user

    @staticmethod
    async def _issue_token(
        user_id: str, remember_days: int = 7
    ) -> tuple[str, str, int]:
        access_token = await createAccessToken(user_id)
        raw_refresh = generateRefreshToken()
        expires_at = datetime.now(UTC) + timedelta(days=remember_days)

        await RefreshToken(
            user_id=PydanticObjectId(user_id),
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=expires_at,
        ).insert()
        max_age = remember_days * 24 * 60 * 60
        return access_token, raw_refresh, max_age

    @staticmethod
    async def rotate_refresh_token(raw_token: str) -> tuple[str, str, int]:
        token_hash = hash_refresh_token(raw_token)
        stored = await RefreshToken.find_one(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
        )

        if not stored or stored.expires_at < datetime.now(UTC):
            if stored:
                await AuthService._revoke_all_for_user(stored.user_id)
            raise UnauthorizedError("Invalid or expired refresh token")

        stored.revoked = True
        await stored.save()
        return await AuthService._issue_token(str(stored.user_id))

    @staticmethod
    async def revoke_refresh_token(raw_token: str) -> None:
        token_hash = hash_refresh_token(raw_token)
        stored = await RefreshToken.find_one(RefreshToken.token_hash == token_hash)
        if stored:
            stored.revoked = True
            await stored.save()

    @staticmethod
    async def _revoke_all_for_user(user_id: PydanticObjectId) -> None:
        await RefreshToken.find(
            RefreshToken.user_id == user_id, RefreshToken.revoked == False
        ).update_many(Set({RefreshToken.revoked: True}))

    @staticmethod
    def get_user_id_from_access_token(token: str) -> str:
        try:
            payload = decodeAccessToken(token).model_dump()
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Invalid or expired access token")
        except jwt.InvalidTokenError:
            raise UnauthorizedError("Invalid or expired access token")

        return payload["sub"]
