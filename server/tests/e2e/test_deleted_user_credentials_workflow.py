"""End-to-end regression: deleting a user must revoke its credentials.

Credentials live in their own table, keyed by user id but looked up by email.
They used to survive the deletion of the user they belonged to, which broke two
things at once:

  - recreating an account on the same address resolved to the leftover row, so
    the correct new password was rejected as invalid;
  - the leftover row still authenticated on its own, because login fell back to
    an empty role set when the user was gone, so deleting a user did not
    actually revoke its ability to log in.
"""

ADMIN = {
    "email": "admin@example.com",
    "password": "admin-password-123",
    "display_name": "System Administrator",
}


def _login_admin(client):
    client.post("/api/auth/register-admin", json=ADMIN)
    client.post("/api/auth/login", json={"email": ADMIN["email"], "password": ADMIN["password"]})


def _create_user(client, email: str, password: str, username: str) -> str:
    response = client.post(
        "/api/users",
        json={
            "username": username,
            "email": email,
            "name": "Test User",
            "password": password,
            "roles": [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_recreating_a_user_on_a_freed_email_can_log_in(client_factory, setup):
    """The exact sequence that used to fail: create, delete, recreate, log in."""
    admin_client = client_factory()
    _login_admin(admin_client)

    email = "contractor@example.com"

    first_id = _create_user(admin_client, email, "first-password-12345", "contractor")
    assert admin_client.delete(f"/api/users/{first_id}").status_code == 204

    _create_user(admin_client, email, "second-password-12345", "contractor2")

    # The new password must be the one that counts, not the deleted account's.
    user_client = client_factory()
    response = user_client.post("/api/auth/login", json={"email": email, "password": "second-password-12345"})
    assert response.status_code == 200, response.text
    assert user_client.get("/api/users/me").json()["email"] == email

    # And the deleted account's password must no longer open anything.
    stale_client = client_factory()
    stale = stale_client.post("/api/auth/login", json={"email": email, "password": "first-password-12345"})
    assert stale.status_code == 401


def test_a_deleted_user_can_no_longer_log_in(client_factory, setup):
    admin_client = client_factory()
    _login_admin(admin_client)

    email = "leaver@example.com"
    password = "leaver-password-12345"

    user_id = _create_user(admin_client, email, password, "leaver")

    # Sanity check: the account works before deletion.
    before = client_factory().post("/api/auth/login", json={"email": email, "password": password})
    assert before.status_code == 200

    assert admin_client.delete(f"/api/users/{user_id}").status_code == 204

    after = client_factory().post("/api/auth/login", json={"email": email, "password": password})
    assert after.status_code == 401
