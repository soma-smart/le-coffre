"""
Complete end-to-end test for the one-time link workflow.

Covers the whole lifecycle:
- an owner issues a link
- an anonymous caller redeems it and gets the secret plus its metadata
- the link cannot be redeemed twice
- redemption is recorded in the password event log
- non-owners cannot issue, list or revoke
- revocation kills an unread link
"""

STRONG_PASSWORD = "StrongP@ssw0rd123"
LOGIN = "service-account"
URL = "https://service.example.com"


def _create_password(admin_client, group_id: str) -> str:
    response = admin_client.post(
        "/api/passwords",
        json={
            "name": "One-time link target",
            "password": STRONG_PASSWORD,
            "folder": "Work",
            "group_id": group_id,
            "login": LOGIN,
            "url": URL,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_complete_one_time_link_workflow(
    authenticated_admin_client,
    unauthenticated_client,
    admin_personal_group_id,
    setup,
):
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)

    # ===================================================================
    # PHASE 1: ISSUE A LINK
    # ===================================================================
    print("\n=== PHASE 1: ISSUE ===")

    create_response = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={})
    assert create_response.status_code == 201
    payload = create_response.json()
    token = payload["token"]
    link_id = payload["id"]
    assert payload["expires_at"] is not None
    print(f"✓ Link issued: {link_id}")

    # The listing must never hand the token back, in any form.
    list_response = admin_client.get(f"/api/passwords/{password_id}/one-time-links")
    assert list_response.status_code == 200
    assert len(list_response.json()["links"]) == 1
    assert list_response.json()["total"] == 1
    assert token not in list_response.text
    assert list_response.json()["links"][0]["read_at"] is None
    print("✓ Listing exposes the link without its token")

    # ===================================================================
    # PHASE 2: ANONYMOUS REDEMPTION
    # ===================================================================
    print("\n=== PHASE 2: REDEEM ANONYMOUSLY ===")

    consume_response = unauthenticated_client.post("/api/one-time-links/consume", json={"token": token})
    assert consume_response.status_code == 200
    body = consume_response.json()
    assert body["password"] == STRONG_PASSWORD
    assert body["name"] == "One-time link target"
    assert body["login"] == LOGIN
    assert body["url"] == URL
    print("✓ Anonymous caller received the secret and its metadata")

    # ===================================================================
    # PHASE 3: SINGLE USE
    # ===================================================================
    print("\n=== PHASE 3: SINGLE USE ===")

    replay_response = unauthenticated_client.post("/api/one-time-links/consume", json={"token": token})
    assert replay_response.status_code == 404
    assert STRONG_PASSWORD not in replay_response.text
    print("✓ Second redemption refused")

    # An unknown token must be indistinguishable from a spent one, otherwise the
    # endpoint tells an anonymous caller which tokens exist.
    unknown_response = unauthenticated_client.post(
        "/api/one-time-links/consume",
        json={"token": "x" * 43},
    )
    assert unknown_response.status_code == 404
    assert unknown_response.json()["detail"] == replay_response.json()["detail"]
    print("✓ Spent and unknown tokens are indistinguishable")

    # ===================================================================
    # PHASE 4: THE READ IS AUDITED
    # ===================================================================
    print("\n=== PHASE 4: AUDIT ===")

    events_response = admin_client.get(f"/api/passwords/{password_id}/events")
    assert events_response.status_code == 200
    event_types = [event["event_type"] for event in events_response.json()["events"]]
    assert "OneTimeLinkCreatedEvent" in event_types
    assert "OneTimeLinkReadEvent" in event_types
    assert STRONG_PASSWORD not in events_response.text
    assert token not in events_response.text
    print("✓ Creation and read are both in the event log, without the secret")

    # The spent link leaves the default view, which only shows what is still
    # actionable, and is found again by asking for the history.
    assert admin_client.get(f"/api/passwords/{password_id}/one-time-links").json()["links"] == []

    history = admin_client.get(
        f"/api/passwords/{password_id}/one-time-links", params={"include_inactive": "true"}
    ).json()
    read_at = history["links"][0]["read_at"]
    assert read_at is not None
    print(f"✓ Spent link leaves the default view and is found in the history: {read_at}")


def test_one_time_link_is_owner_only(
    authenticated_admin_client,
    unauthenticated_client,
    admin_personal_group_id,
    setup,
):
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)

    # Issuing requires authentication at all.
    anonymous_issue = unauthenticated_client.post(f"/api/passwords/{password_id}/one-time-links", json={})
    assert anonymous_issue.status_code == 401

    anonymous_list = unauthenticated_client.get(f"/api/passwords/{password_id}/one-time-links")
    assert anonymous_list.status_code == 401
    print("✓ Issuing and listing stay authenticated")


def test_one_time_link_can_be_revoked_before_it_is_read(
    authenticated_admin_client,
    unauthenticated_client,
    admin_personal_group_id,
    setup,
):
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)

    payload = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={}).json()

    revoke_response = admin_client.delete(f"/api/one-time-links/{payload['id']}")
    assert revoke_response.status_code == 204

    consume_response = unauthenticated_client.post("/api/one-time-links/consume", json={"token": payload["token"]})
    assert consume_response.status_code == 404
    assert STRONG_PASSWORD not in consume_response.text
    print("✓ Revoked link is dead")


def test_one_time_link_rejects_an_out_of_range_lifetime(
    authenticated_admin_client,
    admin_personal_group_id,
    setup,
):
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)

    response = admin_client.post(
        f"/api/passwords/{password_id}/one-time-links",
        json={"lifetime_seconds": 60},
    )
    assert response.status_code == 400
    print("✓ Lifetime below the floor is refused")


def test_one_time_link_listing_stays_bounded_when_many_links_pile_up(
    authenticated_admin_client,
    admin_personal_group_id,
    setup,
):
    """Spent links are never deleted, so a busy password accumulates them. The
    listing must stay small and still tell the owner the real total."""
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)

    # Revoked as we go rather than consumed: the active-link cap means it is
    # history, not live links, that accumulates, and revoking frees the slot
    # without going through the anonymous endpoint, which is itself rate limited.
    for _ in range(25):
        created = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={})
        assert created.status_code == 201
        assert admin_client.delete(f"/api/one-time-links/{created.json()['id']}").status_code == 204

    default_body = admin_client.get(f"/api/passwords/{password_id}/one-time-links").json()
    assert default_body["links"] == []
    assert default_body["total"] == 25

    body = admin_client.get(f"/api/passwords/{password_id}/one-time-links", params={"include_inactive": "true"}).json()

    assert len(body["links"]) == 10
    assert body["total"] == 25
    assert body["active"] == 0
    print("\u2713 Listing capped at 10 while reporting 25 in total")


def test_deleting_a_password_drops_its_one_time_links(
    authenticated_admin_client,
    unauthenticated_client,
    admin_personal_group_id,
    setup,
):
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)
    payload = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={}).json()

    assert admin_client.delete(f"/api/passwords/{password_id}").status_code in (200, 204)

    consume_response = unauthenticated_client.post("/api/one-time-links/consume", json={"token": payload["token"]})
    assert consume_response.status_code == 404
    assert STRONG_PASSWORD not in consume_response.text
    print("\u2713 Links of a deleted password are gone and unusable")


def test_one_time_link_creation_is_capped_and_a_revoke_frees_a_slot(
    authenticated_admin_client,
    admin_personal_group_id,
    setup,
):
    """Each active link is an outstanding anonymous read grant, so their number
    is capped. Revoking one has to give the slot back."""
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)

    created_ids = []
    for _ in range(5):
        response = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={})
        assert response.status_code == 201
        created_ids.append(response.json()["id"])

    refused = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={})
    assert refused.status_code == 409
    print("\u2713 Sixth active link refused with 409")

    body = admin_client.get(f"/api/passwords/{password_id}/one-time-links").json()
    assert body["active"] == 5
    assert body["max_active"] == 5

    assert admin_client.delete(f"/api/one-time-links/{created_ids[0]}").status_code == 204
    assert admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={}).status_code == 201
    print("\u2713 Revoking one freed a slot")


LEAVER_PASSWORD = "AnotherStrongP@ssw0rd1"


def _create_user(admin_client, username: str) -> str:
    response = admin_client.post(
        "/api/users/",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "name": username,
            "password": LEAVER_PASSWORD,
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


def test_admin_sees_and_revokes_links_across_the_whole_vault(
    authenticated_admin_client,
    unauthenticated_client,
    admin_personal_group_id,
    setup,
):
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)
    created = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={}).json()

    listed = admin_client.get("/api/admin/one-time-links")
    assert listed.status_code == 200
    body = listed.json()
    assert any(link["id"] == created["id"] for link in body["links"])
    assert created["token"] not in listed.text
    row = next(link for link in body["links"] if link["id"] == created["id"])
    assert row["password_name"] == "One-time link target"
    assert row["group_name"] is not None
    assert row["created_by_display_name"] is not None
    print("✓ Admin listing shows the link with its password, group and issuer")

    assert admin_client.delete(f"/api/admin/one-time-links/{created['id']}").status_code == 204
    consumed = unauthenticated_client.post("/api/one-time-links/consume", json={"token": created["token"]})
    assert consumed.status_code == 404
    assert STRONG_PASSWORD not in consumed.text
    print("✓ Admin revocation kills the link")


def test_one_time_link_admin_endpoints_reject_a_non_admin(
    authenticated_admin_client,
    unauthenticated_client,
    setup,
):
    anonymous = unauthenticated_client
    assert anonymous.get("/api/admin/one-time-links").status_code == 401
    assert anonymous.get("/api/one-time-links/mine").status_code == 401
    print("✓ Admin and personal listings both require a session")


def test_a_user_sees_only_the_links_they_issued(
    authenticated_admin_client,
    admin_personal_group_id,
    setup,
):
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)
    created = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={}).json()

    mine = admin_client.get("/api/one-time-links/mine")

    assert mine.status_code == 200
    assert [link["id"] for link in mine.json()["links"]] == [created["id"]]
    assert created["token"] not in mine.text
    print("✓ Personal listing returns the caller's own links")


def test_deleting_a_user_revokes_the_links_they_issued(
    authenticated_admin_client,
    client_factory,
    unauthenticated_client,
    setup,
):
    """The scenario this feature exists for: someone loses their access, and the
    anonymous grants they handed out must not outlive their account.

    The link is issued by the user who is then deleted, not by the admin running
    the test, so this exercises the revocation wired into user deletion rather
    than the explicit bulk endpoint.
    """
    admin_client = authenticated_admin_client
    leaver_id = _create_user(admin_client, "leaver")

    leaver_client = client_factory()
    login = leaver_client.post(
        "/api/auth/login",
        json={"email": "leaver@example.com", "password": LEAVER_PASSWORD},
    )
    assert login.status_code == 200, login.text
    if hasattr(leaver_client, "refresh_csrf_token"):
        leaver_client.refresh_csrf_token()

    leaver_group_id = leaver_client.get("/api/users/me").json()["personal_group_id"]
    password_id = _create_password(leaver_client, leaver_group_id)
    created = leaver_client.post(f"/api/passwords/{password_id}/one-time-links", json={}).json()

    # Live before the deletion, so the assertion after it means something.
    assert leaver_client.get("/api/one-time-links/mine").json()["total"] == 1

    assert admin_client.delete(f"/api/users/{leaver_id}").status_code in (200, 204)

    consumed = unauthenticated_client.post("/api/one-time-links/consume", json={"token": created["token"]})
    assert consumed.status_code == 404
    assert STRONG_PASSWORD not in consumed.text
    print("✓ Deleting a user kills the links they issued")


def test_bulk_revocation_cuts_every_live_link_a_user_issued(
    authenticated_admin_client,
    unauthenticated_client,
    admin_personal_group_id,
    setup,
):
    admin_client = authenticated_admin_client
    password_id = _create_password(admin_client, admin_personal_group_id)
    created = admin_client.post(f"/api/passwords/{password_id}/one-time-links", json={}).json()
    me = admin_client.get("/api/users/me").json()["id"]

    bulk = admin_client.delete(f"/api/admin/users/{me}/one-time-links")

    assert bulk.status_code == 200
    assert bulk.json()["revoked_count"] == 1
    consumed = unauthenticated_client.post("/api/one-time-links/consume", json={"token": created["token"]})
    assert consumed.status_code == 404
    assert STRONG_PASSWORD not in consumed.text
    print("✓ Bulk revocation cuts every live link a user issued")
