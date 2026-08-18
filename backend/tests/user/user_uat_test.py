from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import Role

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# UAT-USER-01 & 02: Standard User Profile Endpoints (/user/me)
# --------------------------------------------------------------------------- #


class TestUserMe:
    async def test_get_my_details(self, client: AsyncClient, registered_user):
        """UAT-USER-01: Retrieve authenticated standard user details -> 200 OK, matching email."""
        payload, _ = registered_user
        resp = await client.get("/user/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == payload["email"]

    async def test_update_my_details(self, client: AsyncClient, registered_user):
        """UAT-USER-02: Update authenticated standard user details -> 200 OK, updated fields persisted."""
        payload, _ = registered_user
        resp = await client.patch(
            "/user/me", json={"first_name": "Hello", "last_name": "Testing"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == payload["email"]
        assert data["first_name"] == "Hello"
        assert data["last_name"] == "Testing"


# --------------------------------------------------------------------------- #
# UAT-USER-03 to 08: Admin User Management Endpoints (/user/...)
# --------------------------------------------------------------------------- #


class TestUserAdmin:
    async def test_get_my_details(self, client: AsyncClient, register_admin_user):
        """UAT-USER-04: Retrieve authenticated admin user details -> 200 OK, matching email and ADMIN role."""
        payload, _ = register_admin_user
        resp = await client.get("/user/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == payload["email"]
        assert data["role"] == Role.ADMIN.value

    async def test_get_user_by_id(self, client: AsyncClient, register_admin_user):
        """UAT-USER-05: Retrieve user by valid ID -> 200 OK, matching email and role."""
        payload, _ = register_admin_user
        user_id = payload["id"]
        resp = await client.get(f"/user/id/{user_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == payload["email"]
        assert data["role"] == Role.ADMIN.value

    async def test_get_user_by_non_exist_id(
        self, client: AsyncClient, register_admin_user
    ):
        """UAT-USER-06: Retrieve user by non-existent ID -> 404 Not Found, error message returned."""
        _, _ = register_admin_user
        resp = await client.get("/user/id/6a7f4b613d631e607d7ace57")

        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["message"] == "User not found"

    async def test_get_all_user(self, client: AsyncClient, register_admin_user):
        """UAT-USER-07: Paginated user list retrieval -> 200 OK, returns user list with valid pagination metadata."""
        _, _ = register_admin_user
        resp = await client.get("/user/all?page=1&limit=10")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] != []
        assert data["pagination_meta"]["page"] == 1
        assert data["pagination_meta"]["per_page"] == 10

    async def test_get_all_user_with_search(
        self, client: AsyncClient, register_admin_user
    ):
        """UAT-USER-08: Filtered/Searched user list retrieval -> 200 OK, returns pagination metadata correctly for queries."""
        _, _ = register_admin_user

        # Test with a search query expected to match or return empty/filtered results safely
        resp = await client.get("/user/all?page=1&limit=10&s=ada")
        resp_num = await client.get("/user/all?page=1&limit=10&s=123457890")

        assert resp.status_code == 200
        assert resp_num.status_code == 200

        data = resp.json()
        assert data["pagination_meta"]["page"] == 1
        assert data["pagination_meta"]["per_page"] == 10

    async def test_update_user_by_id_success(
        self, client: AsyncClient, register_admin_user
    ):
        """UAT-USER-09: Update user by valid ID -> 200 OK, updated fields persisted."""
        payload, _ = register_admin_user
        user_id = payload["id"]

        resp = await client.patch(
            f"/user/id/{user_id}", json={"first_name": "Hello", "last_name": "Testing"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == payload["email"]
        assert data["first_name"] == "Hello"
        assert data["last_name"] == "Testing"

    async def test_update_user_by_id_not_found(
        self, client: AsyncClient, register_admin_user
    ):
        """UAT-USER-10: Update non-existent user ID -> 404 Not Found."""
        _, _ = register_admin_user
        non_existent_id = "6a7f4b613d631e607d7ace57"

        resp = await client.patch(
            f"/user/id/{non_existent_id}", json={"first_name": "Ghost"}
        )

        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["message"] == "User not found"

    async def test_update_user_by_id_empty_payload(
        self, client: AsyncClient, register_admin_user
    ):
        """UAT-USER-11: Update with empty payload -> 200 OK, returns user unchanged."""
        payload, _ = register_admin_user
        user_id = payload["id"]

        # Sending empty or unset fields (exclude_unset=True handles this)
        resp = await client.patch(f"/user/id/{user_id}", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == payload["email"]

    async def test_update_user_by_id_email_conflict(
        self, client: AsyncClient, register_admin_user, registered_user
    ):
        """UAT-USER-12: Update user email to one already in use -> 409 Conflict."""
        payload_admin, admin_resp = register_admin_user
        payload_standard, _ = registered_user

        admin_id = payload_admin["id"]
        existing_email = payload_standard["email"]

        access_token = admin_resp.json().get("token", {}).get("access_token")

        client.cookies.set("access_token", access_token)
        resp = await client.patch(
            f"/user/id/{admin_id}", json={"email": existing_email}
        )

        assert resp.status_code == 409
        data = resp.json()
        assert data["error"]["message"] == "Email already registered"

    async def test_update_user_by_id_same_email(
        self, client: AsyncClient, register_admin_user
    ):
        """UAT-USER-13: Update user with their own current email -> 200 OK (no conflict)."""
        payload, _ = register_admin_user
        user_id = payload["id"]
        current_email = payload["email"]

        resp = await client.patch(
            f"/user/id/{user_id}",
            json={"email": current_email, "first_name": "SameEmail"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == current_email
        assert data["first_name"] == "SameEmail"
