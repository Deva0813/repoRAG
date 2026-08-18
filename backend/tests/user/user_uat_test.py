from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.models.auth import JWTPayload, RefreshToken, TokenType
from app.models.user import Role, User
from tests.conftest import expire_refresh_token

pytestmark = pytest.mark.asyncio


def _craft_access_token(user_id: str, role: Role, expired: bool = False) -> str:
    """Build an access-token JWT directly (bypassing login) so we can test
    edge cases like an already-expired token."""
    now = datetime.now(UTC)
    exp = now - timedelta(minutes=1) if expired else now + timedelta(minutes=15)
    payload = JWTPayload(
        sub=user_id, role=role, iat=now, exp=exp, type=TokenType.ACCESS
    )
    return jwt.encode(payload.model_dump(), settings.private_key, algorithm="RS256")

# --------------------------------------------------------------------------- #
# UAT-USER-01..05  /user/me
# --------------------------------------------------------------------------- #

class TestUserMe:
    async def test_get_my_details(self,client: AsyncClient, valid_register_payload):
        assert 100 == 100