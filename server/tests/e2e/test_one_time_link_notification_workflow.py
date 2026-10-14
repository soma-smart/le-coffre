"""
End-to-end: a one-time link's creator is emailed when it is opened or expires unused.

The password context only issues and consumes links; following a link is a
subscription held by the notification context.

1. Only an active link of one's own can be followed
2. Opening a followed link emails its creator (and never leaks the token)
3. Opening a link nobody follows sends nothing
4. A link that expires unread is notified once by the sweep, and only once
5. Read and revoked links are never reported as expired
6. Following no option any more stops the emails
"""

import sqlite3
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
    """Read notifications are sent on an executor thread, after the response returned."""
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


def _create_link(client, password_id: str) -> dict:
    response = client.post(f"/api/passwords/{password_id}/one-time-links", json={})
    assert response.status_code == 201, response.text
    return response.json()


def _follow(client, link_id: str, notify_on_read: bool = False, notify_on_expiry: bool = False):
    return client.put(
        f"/api/notifications/one-time-links/{link_id}",
        json={"notify_on_read": notify_on_read, "notify_on_expiry": notify_on_expiry},
    )


def _consume(client, link: dict) -> None:
    assert client.post("/api/one-time-links/consume", json={"token": link["token"]}).status_code == 200


def _backdate_expiry(database_path: str, link_id: str) -> None:
    """Both contexts hold the expiry: the link itself, and the copy in the subscription."""
    expired = (datetime.now(UTC) - timedelta(minutes=1)).replace(tzinfo=None).isoformat(sep=" ")
    with sqlite3.connect(database_path) as connection:
        for table, key in (("OneTimeLink", "id"), ("OneTimeLinkSubscription", "link_id")):
            connection.execute(
                f'UPDATE "{table}" SET expires_at = ? WHERE {key} = ?', (expired, link_id.replace("-", ""))
            )


def _run_expiry_sweep() -> None:
    """One pass of what the background task runs periodically, against the app's real wiring."""
    main._notify_expired_one_time_links(
        main.app.state.session_maker, main.app.state.email_gateway, main.get_app_base_url()
    )


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
    # PHASE 1: WHAT CAN BE FOLLOWED
    # ===================================================================
    print("\n=== PHASE 1: FOLLOWING ===")

    assert _follow(admin, str(uuid4()), notify_on_read=True).status_code == 404
    already_read = _create_link(admin, password_id)
    _consume(unauthenticated_client, already_read)
    assert _follow(admin, already_read["id"], notify_on_read=True).status_code == 409
    print("✓ Unknown and already read links cannot be followed")

    # ===================================================================
    # PHASE 2: OPENING A FOLLOWED LINK
    # ===================================================================
    print("\n=== PHASE 2: OPENED ===")

    read_link = _create_link(admin, password_id)
    response = _follow(admin, read_link["id"], notify_on_read=True)
    assert response.status_code == 200
    assert response.json() == {"link_id": read_link["id"], "notify_on_read": True, "notify_on_expiry": False}

    _consume(unauthenticated_client, read_link)
    _wait_for_emails(fake_email_gateway, 1)
    email = fake_email_gateway.sent_emails[0]
    assert email["to"] == ADMIN_EMAIL
    assert email["subject"] == "Le Coffre: your one-time link was opened"
    assert 'for "Prod DB" was opened on' in email["body"]
    assert f"{main.get_app_base_url()}/my-links" in email["body"]
    assert read_link["token"] not in email["body"]
    assert STRONG_PASSWORD not in email["body"]
    print("✓ The creator was emailed, and the email carries no token or secret")

    # ===================================================================
    # PHASE 3: OPENING A LINK NOBODY FOLLOWS
    # ===================================================================
    print("\n=== PHASE 3: OPENED, NOT FOLLOWED ===")

    _consume(unauthenticated_client, _create_link(admin, password_id))
    # Emails leave through a single ordered worker: the next one's arrival proves the
    # silent read queued nothing before it.
    followed = _create_link(admin, password_id)
    assert _follow(admin, followed["id"], notify_on_read=True).status_code == 200
    _consume(unauthenticated_client, followed)
    _wait_for_emails(fake_email_gateway, 2)
    assert [e["subject"] for e in fake_email_gateway.sent_emails] == ["Le Coffre: your one-time link was opened"] * 2
    print("✓ A link nobody follows sends no email")

    # ===================================================================
    # PHASE 4: EXPIRY, REPORTED ONCE
    # ===================================================================
    print("\n=== PHASE 4: EXPIRED UNUSED ===")

    expiry_link = _create_link(admin, password_id)
    assert _follow(admin, expiry_link["id"], notify_on_expiry=True).status_code == 200

    # Not expired yet: the sweep has nothing to say.
    _run_expiry_sweep()
    assert len(fake_email_gateway.sent_emails) == 2

    _backdate_expiry(database, expiry_link["id"])
    _run_expiry_sweep()
    assert len(fake_email_gateway.sent_emails) == 3
    email = fake_email_gateway.sent_emails[2]
    assert email["to"] == ADMIN_EMAIL
    assert email["subject"] == "Le Coffre: your one-time link expired unused"
    assert 'for "Prod DB" expired on' in email["body"]
    assert expiry_link["token"] not in email["body"]

    _run_expiry_sweep()
    assert len(fake_email_gateway.sent_emails) == 3
    print("✓ The expired link was reported by the sweep, and only once")

    # ===================================================================
    # PHASE 5: NEVER REPORTED AS EXPIRED
    # ===================================================================
    print("\n=== PHASE 5: NOT REPORTED ===")

    opened_then_expired = _create_link(admin, password_id)
    revoked = _create_link(admin, password_id)
    for link in (opened_then_expired, revoked):
        assert _follow(admin, link["id"], notify_on_expiry=True).status_code == 200
    _consume(unauthenticated_client, opened_then_expired)
    assert admin.delete(f"/api/one-time-links/{revoked['id']}").status_code == 204
    for link in (opened_then_expired, revoked):
        _backdate_expiry(database, link["id"])

    _run_expiry_sweep()
    time.sleep(0.2)
    assert len(fake_email_gateway.sent_emails) == 3
    print("✓ Read and revoked links are never reported as expired")

    # ===================================================================
    # PHASE 6: UNFOLLOWING
    # ===================================================================
    print("\n=== PHASE 6: UNFOLLOWED ===")

    unfollowed = _create_link(admin, password_id)
    assert _follow(admin, unfollowed["id"], notify_on_read=True).status_code == 200
    assert _follow(admin, unfollowed["id"]).status_code == 200
    _consume(unauthenticated_client, unfollowed)
    time.sleep(0.2)
    assert len(fake_email_gateway.sent_emails) == 3
    print("✓ Following no option any more stops the emails")
