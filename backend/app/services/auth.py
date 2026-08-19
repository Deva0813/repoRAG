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
from app.models.auth import JWTPayload, RefreshToken
from app.models.user import User
from app.schemas.auth import LoginData, RegisterData


class AuthService:
    def __init__(self) -> None:
        self.userRepo = User
        self.refreshRepo = RefreshToken

    async def register(self, data: RegisterData):
        existing = await self.userRepo.find_one(self.userRepo.email == data.email)
        if existing:
            raise ConflictError("Email already registered")

        hashed_password = hashPassword(data.password)
        user = self.userRepo(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            hashed_password=hashed_password,
            phone_number=data.phone_number,
        )

        await user.insert()
        return user

    async def authenticate(self, data: LoginData):
        user = await self.userRepo.find_one(self.userRepo.email == data.email)
        if (not user) or (not verifyPassword(data.password, user.hashed_password)):
            raise NotFoundError("Email or Password is invalid")

        return user

    async def issue_token(
        self, user_id: str, remember_days: int = 7
    ) -> tuple[str, str, int]:
        access_token = await createAccessToken(user_id)
        raw_refresh = generateRefreshToken()
        expires_at = datetime.now(UTC) + timedelta(days=remember_days)

        await self.refreshRepo(
            user_id=PydanticObjectId(user_id),
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=expires_at,
        ).insert()
        max_age = remember_days * 24 * 60 * 60
        return access_token, raw_refresh, max_age

    async def rotate_refresh_token(self, raw_token: str) -> tuple[str, str, int]:
        token_hash = hash_refresh_token(raw_token)
        stored = await self.refreshRepo.find_one(
            self.refreshRepo.token_hash == token_hash,
            self.refreshRepo.revoked == False,
        )

        if not stored or stored.expires_at < datetime.now(UTC):
            if stored:
                await self._revoke_all_for_user(stored.user_id)
            raise UnauthorizedError("Invalid or expired refresh token")

        stored.revoked = True
        await stored.save()
        return await self.issue_token(str(stored.user_id))

    async def revoke_refresh_token(self, raw_token: str) -> None:
        token_hash = hash_refresh_token(raw_token)
        stored = await self.refreshRepo.find_one(
            self.refreshRepo.token_hash == token_hash
        )
        if stored:
            stored.revoked = True
            await stored.save()

    async def _revoke_all_for_user(self, user_id: PydanticObjectId) -> None:
        await self.refreshRepo.find(
            self.refreshRepo.user_id == user_id, self.refreshRepo.revoked == False
        ).update_many(Set({self.refreshRepo.revoked: True}))

    def get_user_id_from_access_token(self, token: str):
        try:
            payload: JWTPayload = decodeAccessToken(token)
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Invalid or expired access token")
        except jwt.InvalidTokenError:
            raise UnauthorizedError("Invalid or expired access token")

        return payload.sub
