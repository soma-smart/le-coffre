"""An administrator can disconnect another user's browser extensions.

The case: an account disabled in the identity provider but still present in
the vault, or a laptop reported stolen whose owner is unreachable. Before this
route existed, the only lever an administrator had was deleting the account.
"""

import base64
import hashlib

from tests.e2e.conftest import register_and_login_admin

USER_EMAIL = "paired-user@example.com"
USER_PASSWORD = "securepassword123"


def _pair_extension(client_factory, user_client) -> str:
    """Run the pairing flow for the signed-in user and return the bearer token."""
    verifier = "e2e-admin-revocation-verifier-that-is-long-enough-to-pass"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    device = client_factory()
    registered = device.post(
        "/api/extension/device",
        json={"code_challenge": challenge, "code_challenge_method": "S256", "device_name": "Stolen laptop"},
    )
    assert registered.status_code == 201, registered.text
    user_code = registered.json()["user_code"]
    approved = user_client.post(f"/api/extension/pairing/{user_code}/approve")
    assert approved.status_code == 204, approved.text
    exchanged = device.post("/api/extension/device/exchange", json={"user_code": user_code, "code_verifier": verifier})
    assert exchanged.status_code == 200, exchanged.text
    return exchanged.json()["token"]


def test_admin_can_disconnect_another_users_extensions(e2e_client, client_factory):
    admin_client = e2e_client
    register_and_login_admin(admin_client)
    created = admin_client.post(
        "/api/users",
        json={"username": USER_EMAIL, "email": USER_EMAIL, "name": "Paired User", "password": USER_PASSWORD},
    )
    assert created.status_code in (200, 201), created.text

    user_client = client_factory()
    login = user_client.post("/api/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    assert login.status_code == 200, login.text
    user_id = user_client.get("/api/users/me").json()["id"]
    token = _pair_extension(client_factory, user_client)

    bearer = client_factory()
    headers = {"Authorization": f"Bearer {token}"}
    assert bearer.get("/api/extension/session", headers=headers).status_code == 200

    # A non-admin, the owner included, cannot use the administrative route.
    forbidden = user_client.delete(f"/api/admin/users/{user_id}/extension-tokens")
    assert forbidden.status_code == 403, forbidden.text

    revoked = admin_client.delete(f"/api/admin/users/{user_id}/extension-tokens")
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["revoked_count"] == 1

    # The credential is dead on its next request, and the owner can see why.
    assert bearer.get("/api/extension/session", headers=headers).status_code == 401
    devices = user_client.get("/api/extension/tokens").json()["tokens"]
    assert devices[0]["is_active"] is False
    assert devices[0]["revoked_at"] is not None

    # Idempotent: nothing left to cut.
    assert admin_client.delete(f"/api/admin/users/{user_id}/extension-tokens").json()["revoked_count"] == 0
