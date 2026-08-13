from datetime import datetime
from enum import Enum
from typing import Annotated, ClassVar

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel
from pymongo import IndexModel

from app.models.user import Role


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None


class TokenType(str, Enum):
    ACCESS = "assess"
    REFRESH = "refresh"


class JWTSub(BaseModel):
    user_id: str
    user_role: Role


class JWTPayload(BaseModel):
    sub: JWTSub
    iat: int | datetime
    exp: int | datetime
    type: TokenType


class RefreshToken(Document):
    user_id: PydanticObjectId
    token_hash: Annotated[str, Indexed(unique=True)]
    expires_at: datetime
    revoked: bool = False

    class Settings:
        name = "refresh_tokens"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("expires_at", 1)],
                expireAfterSeconds=0,
                name="expires_at_ttl",
            ),
        ]
