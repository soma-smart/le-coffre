"""A user whose email changes logs in with the new one, and only with it.

The password is checked against a credential record found by email, kept apart
from the email the app shows. Both must move together, or the account shows an
address it refuses at login.
"""

from tests.e2e.conftest import register_and_login_admin

PASSWORD = "SecurePassword123!"


def _create_user(admin_client, email: str) -> str:
    created = admin_client.post(
        "/api/users",
        json={"username": email.split("@")[0], "email": email, "name": "Alice", "password": PASSWORD},
    )
    assert created.status_code in (200, 201), created.text
    return created.json()["id"]


def _login(client_factory, email: str) -> int:
    return client_factory().post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code


def test_given_an_admin_changing_a_users_email_when_logging_in_then_only_the_new_email_works(
    e2e_client, client_factory
):
    admin_client = e2e_client
    register_and_login_admin(admin_client)
    user_id = _create_user(admin_client, "alice@old.fr")

    updated = admin_client.put(
        f"/api/users/{user_id}", json={"username": "alice", "email": "alice@new.fr", "name": "Alice"}
    )
    assert updated.status_code == 200, updated.text

    assert _login(client_factory, "alice@new.fr") == 200
    assert _login(client_factory, "alice@old.fr") == 401


def test_given_a_freed_email_when_another_user_takes_it_then_it_does_not_open_the_first_account(
    e2e_client, client_factory
):
    admin_client = e2e_client
    register_and_login_admin(admin_client)
    alice_id = _create_user(admin_client, "alice@old.fr")
    bob_id = _create_user(admin_client, "bob@example.com")

    admin_client.put(f"/api/users/{alice_id}", json={"username": "alice", "email": "alice@new.fr", "name": "Alice"})
    taken = admin_client.put(f"/api/users/{bob_id}", json={"username": "bob", "email": "alice@old.fr", "name": "Bob"})
    assert taken.status_code == 200, taken.text

    bob_client = client_factory()
    assert bob_client.post("/api/auth/login", json={"email": "alice@old.fr", "password": PASSWORD}).status_code == 200
    assert bob_client.get("/api/users/me").json()["id"] == bob_id
