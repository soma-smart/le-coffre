"""
End-to-end: a one-time link's creator is emailed when it is opened or expires unused.

1. Defaults: a link created without the new options notifies nobody
2. Options are stored and listed back
3. Opening a link that asked for it emails its creator (and never leaks the token)
4. Opening a link that did not ask sends nothing
5. A link that expires unread is notified once by the sweep, and only once
6. Read, revoked and not-yet-expired links are never reported as expired
"""

import sqlite3
import time
from datetime import UTC, datetime, timedelta

import pytest

import main
from tests.shared_kernel.fakes import FakeEmailGateway

STRONG_PASSWORD = "StrongP@ssw0rd123"
ADMIN_EMAIL = "admin@example.com"


@pytest.fixture
def fake_email_gateway(monkeypatch):
    """The app builds its SMTP gateway in its lifespan: swap it for a fake before it starts."""
    gateway = FakeEmailGateway()
    monkeypatch.setattr(main, "SmtpEmailGateway", lambda **_: gateway)
    return gateway


@pytest.fixture
def e2e_client(fake_email_gateway, e2e_client):
    # Same fixture name on purpose: guarantees the fake is in place before the lifespan runs.
    return e2e_client


def _wait_for_emails(gateway: FakeEmailGateway, count: int, timeout: float = 5.0) -> None:
    """Notifications are sent on an executor thread, after the response returned."""
    deadline = time.monotonic() + timeout
    while len(gateway.sent_emails) < count and time.monotonic() < deadline:
        time.sleep(0.02)
    assert len(gateway.sent_emails) == count, f"expected {count} email(s), got {gateway.sent_emails}"


def _create_password(client, group_id: str) -> str:
    response = client.post(
        "/api/passwords",
        json={"name": "Prod DB", "password": STRONG_PASSWORD, "folder": "Work", "group_id": group_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_link(client, password_id: str, **options) -> dict:
    response = client.post(f"/api/passwords/{password_id}/one-time-links", json=options)
    assert response.status_code == 201, response.text
    return response.json()


def _backdate_expiry(database_path: str, link_id: str) -> None:
    expired = (datetime.now(UTC) - timedelta(minutes=1)).replace(tzinfo=None).isoformat(sep=" ")
    with sqlite3.connect(database_path) as connection:
        connection.execute('UPDATE "OneTimeLink" SET expires_at = ? WHERE id = ?', (expired, link_id.replace("-", "")))


def _run_expiry_sweep() -> None:
    """One pass of what the background task runs periodically, against the app's real wiring."""
    main._publish_expired_one_time_links(main.app.state.session_maker, main.app.state.domain_event_publisher)


def test_complete_one_time_link_notification_workflow(
    authenticated_admin_client,
    unauthenticated_client,
    admin_personal_group_id,
    fake_email_gateway,
    database,
    setup,
):
    admin = authenticated_admin_client
    password_id = _create_password(admin, admin_personal_group_id)

    # ===================================================================
    # PHASE 1: DEFAULTS
    # ===================================================================
    print("\n=== PHASE 1: DEFAULTS ===")

    plain = _create_link(admin, password_id)
    listing = admin.get(f"/api/passwords/{password_id}/one-time-links").json()["links"]
    assert [(link["notify_on_read"], link["notify_on_expiry"]) for link in listing] == [(False, False)]
    print("✓ A link created without the options notifies nobody")

    # ===================================================================
    # PHASE 2: OPTIONS ARE STORED
    # ===================================================================
    print("\n=== PHASE 2: OPTIONS ===")

    read_link = _create_link(admin, password_id, notify_on_read=True)
    expiry_link = _create_link(admin, password_id, notify_on_expiry=True)
    flags = {
        link["id"]: (link["notify_on_read"], link["notify_on_expiry"])
        for link in admin.get(f"/api/passwords/{password_id}/one-time-links").json()["links"]
    }
    assert flags == {
        plain["id"]: (False, False),
        read_link["id"]: (True, False),
        expiry_link["id"]: (False, True),
    }
    print("✓ Both options are stored independently and listed back")

    # ===================================================================
    # PHASE 3: OPENING A LINK THAT ASKED TO BE REPORTED
    # ===================================================================
    print("\n=== PHASE 3: OPENED ===")

    response = unauthenticated_client.post("/api/one-time-links/consume", json={"token": read_link["token"]})
    assert response.status_code == 200
    _wait_for_emails(fake_email_gateway, 1)
    email = fake_email_gateway.sent_emails[0]
    assert email["to"] == ADMIN_EMAIL
    assert email["subject"] == "Le Coffre: your one-time link was opened"
    assert 'for "Prod DB" was opened on' in email["body"]
    assert "http://localhost:8123/my-links" in email["body"]
    assert read_link["token"] not in email["body"]
    assert STRONG_PASSWORD not in email["body"]
    print("✓ The creator was emailed, and the email carries no token or secret")

    # ===================================================================
    # PHASE 4: OPENING A LINK THAT DID NOT ASK
    # ===================================================================
    print("\n=== PHASE 4: OPENED, NOT REQUESTED ===")

    assert unauthenticated_client.post("/api/one-time-links/consume", json={"token": plain["token"]}).status_code == 200
    # Emails leave through a single ordered worker: the next one's arrival proves the
    # silent read queued nothing before it.
    flagged = _create_link(admin, password_id, notify_on_read=True)
    unauthenticated_client.post("/api/one-time-links/consume", json={"token": flagged["token"]})
    _wait_for_emails(fake_email_gateway, 2)
    assert [e["subject"] for e in fake_email_gateway.sent_emails] == ["Le Coffre: your one-time link was opened"] * 2
    print("✓ A link that did not ask sends no email")

    # ===================================================================
    # PHASE 5: EXPIRY, REPORTED ONCE
    # ===================================================================
    print("\n=== PHASE 5: EXPIRED UNUSED ===")

    # Not expired yet: the sweep has nothing to say.
    _run_expiry_sweep()
    assert len(fake_email_gateway.sent_emails) == 2

    _backdate_expiry(database, expiry_link["id"])
    _run_expiry_sweep()
    _wait_for_emails(fake_email_gateway, 3)
    email = fake_email_gateway.sent_emails[2]
    assert email["to"] == ADMIN_EMAIL
    assert email["subject"] == "Le Coffre: your one-time link expired unused"
    assert 'for "Prod DB" expired on' in email["body"]
    assert expiry_link["token"] not in email["body"]

    _run_expiry_sweep()
    time.sleep(0.2)
    assert len(fake_email_gateway.sent_emails) == 3
    print("✓ The expired link was reported by the sweep, and only once")

    # ===================================================================
    # PHASE 6: NEVER REPORTED AS EXPIRED
    # ===================================================================
    print("\n=== PHASE 6: NOT REPORTED ===")

    opened_then_expired = _create_link(admin, password_id, notify_on_expiry=True)
    unauthenticated_client.post("/api/one-time-links/consume", json={"token": opened_then_expired["token"]})
    revoked = _create_link(admin, password_id, notify_on_expiry=True)
    assert admin.delete(f"/api/one-time-links/{revoked['id']}").status_code == 204
    for link in (opened_then_expired, revoked):
        _backdate_expiry(database, link["id"])

    _run_expiry_sweep()
    time.sleep(0.2)
    assert len(fake_email_gateway.sent_emails) == 3
    print("✓ Read and revoked links are never reported as expired")
