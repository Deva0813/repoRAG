"""
Automated regression tests for the Auth module, mirroring the UAT test
cases (UAT-AUTH-01 .. UAT-AUTH-20) documented for /auth/register,
/auth/login, /auth/refresh, /auth/logout, and the is_authenticated /
RBAC guard.

Run with:
    pytest tests/test_auth.py -v
"""

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
# UAT-AUTH-01..05  /auth/register
# --------------------------------------------------------------------------- #


class TestRegister:
    async def test_register_success(self, client: AsyncClient, valid_register_payload):
        """UAT-AUTH-01: complete valid payload -> 201, profile + tokens, cookies set."""
        resp = await client.post("/auth/register", json=valid_register_payload)

        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == valid_register_payload["email"]
        assert body["first_name"] == valid_register_payload["first_name"]
        assert body["token"]["access_token"]
        assert body["token"]["refresh_token"]

        assert "access_token" in resp.cookies
        assert "refresh_token" in resp.cookies

    async def test_register_duplicate_email(self, client: AsyncClient, registered_user):
        """UAT-AUTH-02: re-using an existing email -> 409 Conflict."""
        payload, _ = registered_user
        resp = await client.post("/auth/register", json=payload)

        assert resp.status_code == 409
        assert resp.json()["error"]["message"] == "Email already registered"

    async def test_register_minimal_fields(self, client: AsyncClient):
        """UAT-AUTH-03: only email + password -> 201, optional fields empty."""
        resp = await client.post(
            "/auth/register",
            json={"email": "minimal@example.com", "password": "Passw0rd!"},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "minimal@example.com"
        assert body["first_name"] is None
        assert body["phone_number"] is None

    async def test_register_invalid_email(self, client: AsyncClient):
        """UAT-AUTH-04: malformed email -> 422 validation error."""
        resp = await client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "Passw0rd!"},
        )

        assert resp.status_code == 422

    async def test_register_missing_password(self, client: AsyncClient):
        """UAT-AUTH-05: password omitted -> 422 validation error."""
        resp = await client.post("/auth/register", json={"email": "nopass@example.com"})

        assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# UAT-AUTH-06..09  /auth/login
# --------------------------------------------------------------------------- #


class TestLogin:
    async def test_login_success(self, client: AsyncClient, registered_user):
        """UAT-AUTH-06: correct credentials -> 200, tokens + cookies."""
        payload, _ = registered_user
        # fresh client so we don't reuse cookies from registration
        resp = await client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == payload["email"]
        assert body["token"]["access_token"]
        assert "access_token" in resp.cookies
        assert "refresh_token" in resp.cookies

    async def test_login_wrong_password(self, client: AsyncClient, registered_user):
        """UAT-AUTH-07: correct email, wrong password -> 404, generic message."""
        payload, _ = registered_user
        resp = await client.post(
            "/auth/login",
            json={"email": payload["email"], "password": "WrongPassword!"},
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["message"] == "Email or Password is invalid"
        assert "access_token" not in resp.cookies

    async def test_login_unknown_email(self, client: AsyncClient):
        """UAT-AUTH-08: unregistered email -> same generic 404 (no user enumeration)."""
        resp = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "Whatever1!"},
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["message"] == "Email or Password is invalid"

    async def test_login_remember_me_extends_session(
        self, client: AsyncClient, registered_user
    ):
        """UAT-AUTH-09: remember_me=true -> refresh cookie max-age ~30 days,
        longer than the default (~7 day) session."""
        payload, _ = registered_user

        default_resp = await client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        remembered_resp = await client.post(
            "/auth/login",
            json={
                "email": payload["email"],
                "password": payload["password"],
                "remember_me": True,
            },
        )

        default_max_age = _cookie_max_age(default_resp, "refresh_token")
        remembered_max_age = _cookie_max_age(remembered_resp, "refresh_token")

        assert default_max_age == settings.refresh_token_expire_days * 24 * 60 * 60
        assert (
            remembered_max_age == settings.refresh_token_expire_days_max * 24 * 60 * 60
        )
        assert remembered_max_age > default_max_age


def _cookie_max_age(resp, cookie_name: str) -> int:
    """Pull Max-Age off a Set-Cookie header for the given cookie name."""
    for header in resp.headers.get_list("set-cookie"):
        if header.startswith(f"{cookie_name}="):
            for part in header.split(";"):
                part = part.strip()
                if part.lower().startswith("max-age="):
                    return int(part.split("=", 1)[1])
    raise AssertionError(f"{cookie_name} cookie not found in response")


# --------------------------------------------------------------------------- #
# UAT-AUTH-10..13  /auth/refresh
# --------------------------------------------------------------------------- #


class TestRefresh:
    async def test_refresh_valid_token_rotates(
        self, client: AsyncClient, registered_user
    ):
        """UAT-AUTH-10: valid refresh cookie -> 200, new tokens, old one rotated."""
        _, register_resp = registered_user
        old_refresh = register_resp.cookies["refresh_token"]

        resp = await client.post("/auth/refresh")

        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        new_refresh = resp.cookies.get("refresh_token")
        assert new_refresh and new_refresh != old_refresh

        # The old refresh token must now be rejected (rotation enforced).
        client.cookies.set("refresh_token", old_refresh)
        reuse_resp = await client.post("/auth/refresh")
        assert reuse_resp.status_code == 401

    async def test_refresh_missing_cookie(self, client: AsyncClient):
        """UAT-AUTH-11: no refresh_token cookie -> 401 'Missing refresh token'."""
        resp = await client.post("/auth/refresh")

        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Missing refresh token"

    async def test_refresh_expired_token(self, client: AsyncClient, registered_user):
        """UAT-AUTH-12: expired refresh token -> 401, and it revokes the
        user's other active sessions."""
        payload, _ = registered_user
        await expire_refresh_token(payload["email"])

        resp = await client.post("/auth/refresh")

        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Invalid or expired refresh token"

        user = await User.find_one(User.email == payload["email"])
        assert user != None
        remaining_active = await RefreshToken.find(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,
        ).count()
        assert remaining_active == 0

    async def test_refresh_token_reuse_detected(
        self, client: AsyncClient, registered_user
    ):
        """UAT-AUTH-13: replaying an already-rotated/revoked refresh token
        is rejected."""
        _, register_resp = registered_user
        old_refresh = register_resp.cookies["refresh_token"]

        # Rotate once (consumes the token) ...
        await client.post("/auth/refresh")
        # ... then try to reuse the original, already-consumed token.
        client.cookies.set("refresh_token", old_refresh)
        resp = await client.post("/auth/refresh")

        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Invalid or expired refresh token"


# --------------------------------------------------------------------------- #
# UAT-AUTH-14..15  /auth/logout
# --------------------------------------------------------------------------- #


class TestLogout:
    async def test_logout_active_session(self, client: AsyncClient, registered_user):
        """UAT-AUTH-14: logout with an active session -> 204, token revoked,
        cookies cleared."""
        payload, _ = registered_user

        resp = await client.post("/auth/logout")

        assert resp.status_code == 204
        set_cookie_headers = resp.headers.get_list("set-cookie")
        assert any(
            h.startswith("refresh_token=") and "Max-Age=0" in h
            for h in set_cookie_headers
        )
        assert any(
            h.startswith("access_token=") and "Max-Age=0" in h
            for h in set_cookie_headers
        )

        user = await User.find_one(User.email == payload["email"])
        assert user != None
        token = await RefreshToken.find_one(RefreshToken.user_id == user.id)
        assert token != None
        assert token.revoked is True

    async def test_logout_without_cookie(self, client: AsyncClient):
        """UAT-AUTH-15: logout with no session -> still 204, idempotent."""
        resp = await client.post("/auth/logout")

        assert resp.status_code == 204


# --------------------------------------------------------------------------- #
# UAT-AUTH-16..20  Protected routes / is_authenticated / RBAC
# --------------------------------------------------------------------------- #


class TestProtectedRoutes:
    async def test_access_with_valid_access_token(
        self, client: AsyncClient, registered_user
    ):
        """UAT-AUTH-16: valid access token -> request succeeds as that user."""
        payload, _ = registered_user

        resp = await client.get("/user/me")

        assert resp.status_code == 200
        assert resp.json()["email"] == payload["email"]

    async def test_silent_refresh_on_expired_access_token(
        self, client: AsyncClient, registered_user
    ):
        """UAT-AUTH-17: access token expired but refresh token valid -> the
        request still succeeds and new cookies are silently issued."""
        payload, _ = registered_user
        user = await User.find_one(User.email == payload["email"])
        assert user != None
        expired_token = _craft_access_token(str(user.id), user.role, expired=True)
        client.cookies.set("access_token", expired_token)

        resp = await client.get("/user/me")

        assert resp.status_code == 200
        assert resp.json()["email"] == payload["email"]
        new_access = resp.cookies.get("access_token")
        assert new_access and new_access != expired_token

    async def test_no_tokens_present(self, client: AsyncClient):
        """UAT-AUTH-18: no cookies at all -> 401 'Session expired'."""
        resp = await client.get("/user/me")

        assert resp.status_code == 401
        assert resp.json()["error"]["message"] == "Session expired, please log in again"

    async def test_tampered_access_token_no_refresh(self, client: AsyncClient):
        """UAT-AUTH-19: corrupted access token and no refresh token -> 401
        'Could not validate credentials'."""
        client.cookies.set("access_token", "not-a-real.jwt.token")

        resp = await client.get("/user/me")

        assert resp.status_code == 401
        assert (
            resp.json()["error"]["message"]
            == "Unauthorized: Could not validate credentials"
        )

    async def test_rbac_insufficient_role(self, client: AsyncClient, registered_user):
        """UAT-AUTH-20: authenticated USER hitting an admin-only route -> 403."""
        payload, _ = registered_user
        user = await User.find_one(User.email == payload["email"])
        assert user != None
        assert user.role == Role.USER  # default role sanity check

        resp = await client.get(f"/user/id/{user.id}")

        assert resp.status_code == 403
        assert resp.json()["error"]["message"] == "Not enough permissions"
