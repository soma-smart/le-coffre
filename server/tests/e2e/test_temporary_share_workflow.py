"""End-to-end test for time-limited password sharing.

Covers the whole loop through FastAPI: share with a deadline, see it on both the
recipient's listing and the owner's access panel, then retime it: extend it,
shorten it, and lift it entirely.

Expiry itself is driven by the server clock, so a test cannot fast-forward past
a deadline without reaching around the API. Losing access at the deadline is
covered by the use-case unit tests, which own a fake clock.
"""

from datetime import UTC, datetime, timedelta

STRONG_PASSWORD = "StrongP@ssw0rd123"


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def test_temporary_share_workflow(client_factory, setup, configured_sso, sso_user_token):
    admin_client = client_factory()
    sso_client = client_factory()

    admin_client.post(
        "/api/auth/register-admin",
        json={
            "email": "admin@example.com",
            "password": "admin-password-123",
            "display_name": "System Administrator",
        },
    )
    admin_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-password-123"},
    )
    sso_client.cookies.set("access_token", sso_user_token["token"])

    admin_group_id = admin_client.get("/api/users/me").json()["personal_group_id"]
    sso_user = sso_client.get("/api/users/me").json()
    sso_group_id = sso_user["personal_group_id"]

    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Contractor Access",
            "password": STRONG_PASSWORD,
            "folder": "Shared",
            "group_id": admin_group_id,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    now = datetime.now(UTC)
    in_one_hour = now + timedelta(hours=1)

    # Share for an hour
    share_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_group_id, "expires_at": _iso(in_one_hour)},
    )
    assert share_response.status_code == 201

    # The recipient can read it, and is told when their access lapses
    assert sso_client.get(f"/api/passwords/{password_id}").status_code == 200
    recipient_entry = next(p for p in sso_client.get("/api/passwords/list").json() if p["id"] == password_id)
    assert datetime.fromisoformat(recipient_entry["access_expires_at"]) == in_one_hour
    assert recipient_entry["can_write"] is False

    # The owner's own access never lapses
    owner_entry = next(p for p in admin_client.get("/api/passwords/list").json() if p["id"] == password_id)
    assert owner_entry["access_expires_at"] is None

    # The deadline shows up on the access panel, against the shared group only
    access = admin_client.get(f"/api/passwords/{password_id}/access").json()
    shared_group = next(g for g in access["group_access_list"] if g["group_id"] == sso_group_id)
    owner_group = next(g for g in access["group_access_list"] if g["group_id"] == admin_group_id)
    assert datetime.fromisoformat(shared_group["expires_at"]) == in_one_hour
    assert owner_group["expires_at"] is None
    shared_user = next(u for u in access["user_access_list"] if u["group_id"] == sso_group_id)
    assert datetime.fromisoformat(shared_user["expires_at"]) == in_one_hour

    # Extend it
    in_a_month = now + timedelta(days=30)
    extend_response = admin_client.patch(
        f"/api/passwords/{password_id}/share/{sso_group_id}",
        json={"expires_at": _iso(in_a_month)},
    )
    assert extend_response.status_code == 204
    access = admin_client.get(f"/api/passwords/{password_id}/access").json()
    shared_group = next(g for g in access["group_access_list"] if g["group_id"] == sso_group_id)
    assert datetime.fromisoformat(shared_group["expires_at"]) == in_a_month

    # Make it permanent
    permanent_response = admin_client.patch(
        f"/api/passwords/{password_id}/share/{sso_group_id}",
        json={"expires_at": None},
    )
    assert permanent_response.status_code == 204
    access = admin_client.get(f"/api/passwords/{password_id}/access").json()
    shared_group = next(g for g in access["group_access_list"] if g["group_id"] == sso_group_id)
    assert shared_group["expires_at"] is None
    assert sso_client.get(f"/api/passwords/{password_id}").status_code == 200

    # Revoking still works on a share that went through the temporary path
    assert admin_client.delete(f"/api/passwords/{password_id}/share/{sso_group_id}").status_code == 204
    assert sso_client.get(f"/api/passwords/{password_id}").status_code == 404


def test_temporary_share_rejects_invalid_deadlines(client_factory, setup, configured_sso, sso_user_token):
    admin_client = client_factory()
    sso_client = client_factory()

    admin_client.post(
        "/api/auth/register-admin",
        json={
            "email": "admin@example.com",
            "password": "admin-password-123",
            "display_name": "System Administrator",
        },
    )
    admin_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-password-123"},
    )
    sso_client.cookies.set("access_token", sso_user_token["token"])

    admin_group_id = admin_client.get("/api/users/me").json()["personal_group_id"]
    sso_group_id = sso_client.get("/api/users/me").json()["personal_group_id"]

    password_id = admin_client.post(
        "/api/passwords",
        json={
            "name": "Bad Deadlines",
            "password": STRONG_PASSWORD,
            "folder": "Shared",
            "group_id": admin_group_id,
        },
    ).json()["id"]

    now = datetime.now(UTC)

    past = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_group_id, "expires_at": _iso(now - timedelta(minutes=5))},
    )
    assert past.status_code == 400

    # Nothing was granted by the rejected attempt
    assert sso_client.get(f"/api/passwords/{password_id}").status_code == 404

    # A deadline years out is fine: sharing permanently is already unbounded,
    # so refusing a long share would only push the owner towards a permanent one.
    far = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_group_id, "expires_at": _iso(now + timedelta(days=365 * 5))},
    )
    assert far.status_code == 201
    assert admin_client.delete(f"/api/passwords/{password_id}/share/{sso_group_id}").status_code == 204

    # Retiming a share that does not exist
    missing = admin_client.patch(
        f"/api/passwords/{password_id}/share/{sso_group_id}",
        json={"expires_at": _iso(now + timedelta(days=1))},
    )
    assert missing.status_code == 404

    # A non-owner cannot retime a share
    admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_group_id, "expires_at": _iso(now + timedelta(days=1))},
    )
    forbidden = sso_client.patch(
        f"/api/passwords/{password_id}/share/{sso_group_id}",
        json={"expires_at": _iso(now + timedelta(days=30))},
    )
    assert forbidden.status_code == 403
