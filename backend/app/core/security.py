import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.models.auth import JWTPayload, JWTSub, TokenType
from app.services.user import UserService

# -------------------------------- Password Hashing --------------------------------#

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hashPassword(password: str) -> str:
    return pwd_context.hash(password)


def verifyPassword(password: str, hashedPassword: str) -> bool:
    return pwd_context.verify(password, hashedPassword)


# ------------------------------ Access Token (JWT) ------------------------------#


async def createAccessToken(user_id: str) -> str:
    now = datetime.now(UTC)

    user = await UserService.findById(user_id)

    payload = JWTPayload(
        sub=JWTSub(user_id=str(user.id), user_role=user.role),
        iat=now,
        exp=now + timedelta(minutes=settings.access_token_expire_minutes),
        type=TokenType.ACCESS,
    )

    return jwt.encode(
        payload.model_dump(), settings.jwt_access_secret, algorithm="HS256"
    )


def decodeAccessToken(token: str) -> JWTPayload:
    return JWTPayload(
        **jwt.decode(token, settings.jwt_access_secret, algorithms="HS256")
    )


# ------------------------ Refresh Token (opaque,No JWT) ------------------------#


def generateRefreshToken() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
