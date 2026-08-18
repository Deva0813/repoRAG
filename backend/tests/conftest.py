from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from beanie import init_beanie
from bson.codec_options import CodecOptions
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from mongomock.database import Database as _MongomockDatabase
from mongomock_motor import AsyncMongoMockClient

from app.core.config import settings
from app.core.error import NotFoundError
from app.main import app
from app.models.auth import RefreshToken
from app.models.user import User

_original_list_collection_names = _MongomockDatabase.list_collection_names


def _list_collection_names_compat(self, filter=None, session=None, **_ignored):
    return _original_list_collection_names(self, filter=filter, session=session)


_MongomockDatabase.list_collection_names = _list_collection_names_compat

# --------------------------------------------------------------------------- #
# Settings overrides (must happen before any auth flow runs)
# --------------------------------------------------------------------------- #

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
_PUBLIC_PEM = (
    _key.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode()
)

settings.private_key = _PRIVATE_PEM
settings.public_key = _PUBLIC_PEM
settings.cookie_secure = False
settings.access_token_expire_minutes = 15
settings.refresh_token_expire_days = 7
settings.refresh_token_expire_days_max = 30


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    """Fresh in-memory Mongo database per test - full isolation, no bleed-through.

    `codec_options=CodecOptions(tz_aware=True)` mirrors the production client
    (`AsyncMongoClient(..., tz_aware=True)` in app/core/db.py) so datetimes
    round-trip as timezone-aware, matching real Mongo behaviour - otherwise
    mongomock hands back naive datetimes and breaks aware/naive comparisons
    in the app code (e.g. refresh-token expiry checks).
    """
    client = AsyncMongoMockClient()
    db:Any = client.get_database("reporag_test", codec_options=CodecOptions(tz_aware=True))
    await init_beanie(database=db, document_models=[User, RefreshToken])  # type: ignore
    yield
    client.close()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client wired directly to the ASGI app, cookie-jar enabled."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def valid_register_payload():
    return {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada.lovelace@example.com",
        "password": "Str0ngPassw0rd!",
        "phone_number": {
            "number": 123457890,
            "country_code": 91,
            "country": "IN",
            "prefix": "+91",
        },
    }


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, valid_register_payload: dict):
    resp = await client.post("/auth/register", json=valid_register_payload)
    assert resp.status_code == 201, resp.text
    return valid_register_payload, resp

@pytest_asyncio.fixture
async def register_admin_user(client: AsyncClient, valid_register_payload: dict):
    resp = await client.post("/auth/register", json=valid_register_payload)
    user = await User.find_one(User.email == valid_register_payload.get("email"))
    assert resp.status_code == 201, resp.text
    return valid_register_payload, resp


async def expire_refresh_token(email: str) -> None:
    user = await User.find_one(User.email == email)
    if not user: raise NotFoundError("No User Found")
    token = await RefreshToken.find_one(RefreshToken.user_id == user.id)
    if not token: raise NotFoundError("No Token Found")
    await RefreshToken.get_pymongo_collection().update_one(
        {"_id": token.id},
        {"$set": {"expires_at": datetime.now(UTC) - timedelta(days=1)}},
    )


async def revoke_refresh_token(email: str) -> None:
    user = await User.find_one(User.email == email)
    if not user: raise NotFoundError("No User Found")
    token = await RefreshToken.find_one(RefreshToken.user_id == user.id)
    if not token: raise NotFoundError("No Token Found")
    await RefreshToken.get_pymongo_collection().update_one(
        {"_id": token.id}, {"$set": {"revoked": True}}
    )
