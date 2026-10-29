"""
End-to-end test for the links distributing the Shamir shares at vault setup.

Covers:
- setup hands out one link per share and never a share in clear
- a custodian with no account retrieves their share, may reopen the link
  until they acknowledge it, and never after
- what the database holds can neither reveal a share nor rebuild the master key
- links keep working while the vault is locked (when the shares are needed)
- a re-setup kills the links of the abandoned attempt
- the retrieved shares unlock the vault
"""

import base64
import hashlib

import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import create_engine, text

from security.rate_limiter import InMemoryRateLimiter
from tests.vault_management_context.share_link_crypto import (
    acknowledge_share,
    open_retrieved_share,
    open_sealed_share,
    retrieve_share,
    share_link_ack_key,
    share_link_lookup_hash,
)

UNUSABLE_DETAIL = "This share link is invalid, expired or has already been used"


def _retrieve(client, token: str):
    return client.post("/api/vault/share-links/retrieve", json={"lookup_hash": share_link_lookup_hash(token)})


def _register_admin_and_login(client) -> None:
    client.post(
        "/api/auth/register-admin",
        json={"email": "admin@example.com", "password": "admin-password-123", "display_name": "Admin"},
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "admin@example.com", "password": "admin-password-123"}
        ).status_code
        == 200
    )
    client.refresh_csrf_token()


def _share_link_rows(database_path: str) -> list[dict]:
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.connect() as conn:
        rows = [dict(row._mapping) for row in conn.execute(text('SELECT * FROM "VaultShareLink"'))]
    engine.dispose()
    return rows


def test_vault_share_link_workflow(e2e_client, client_factory, database):
    database_path = database
    custodian = client_factory()

    # === SETUP: before any account exists, as in the real bootstrap ===
    setup_response = e2e_client.post("/api/vault/setup", json={"nb_shares": 3, "threshold": 2})
    assert setup_response.status_code == 201
    setup = setup_response.json()
    assert "shares" not in setup
    links = setup["share_links"]
    assert [link["share_index"] for link in links] == [1, 2, 3]
    assert len({link["token"] for link in links}) == 3
    assert all(link["expires_at"] for link in links)

    # The database keeps neither the tokens nor anything that opens the shares.
    rows = _share_link_rows(database_path)
    assert len(rows) == 3
    for row, link in zip(sorted(rows, key=lambda r: r["share_index"]), links, strict=True):
        assert row["lookup_hash"] == share_link_lookup_hash(link["token"])
        assert row["ack_hash"] != share_link_ack_key(link["token"])
        assert link["token"] not in str(row)
        assert row["sealed_share"]
        assert row["delivered_at"] is None

    # === RETRIEVE: anonymous, no CSRF token, no session ===
    first_share = retrieve_share(custodian, links[0]["token"])
    assert first_share.startswith("1:")

    # Retrieved but not yet acknowledged: the link stays, so a lost response or
    # a closed tab does not cost the share.
    delivered = {row["share_index"]: row for row in _share_link_rows(database_path)}[1]
    assert delivered["delivered_at"] is not None

    # === REOPEN: flagged, with the time of the first opening ===
    reopened = _retrieve(custodian, links[0]["token"])
    assert reopened.status_code == 200
    assert reopened.json()["reopened"] is True
    assert open_retrieved_share(reopened.json(), links[0]["token"]) == first_share

    # === ACKNOWLEDGE: knowing the lookup hash is not enough, the token is needed ===
    forged = custodian.post(
        "/api/vault/share-links/acknowledge",
        json={"lookup_hash": share_link_lookup_hash(links[0]["token"]), "ack_key": "0" * 64},
    )
    assert forged.status_code == 403
    acknowledge_share(custodian, links[0]["token"])
    assert sorted(row["share_index"] for row in _share_link_rows(database_path)) == [2, 3]

    # === CLOSED: a retrieval after acknowledgement gets the same answer as an unknown link ===
    replay = _retrieve(custodian, links[0]["token"])
    unknown = _retrieve(custodian, "never-issued")
    assert replay.status_code == unknown.status_code == 404
    assert replay.json() == unknown.json() == {"detail": UNUSABLE_DETAIL}

    # A link nobody retrieved cannot be acknowledged
    not_retrieved = custodian.post(
        "/api/vault/share-links/acknowledge",
        json={
            "lookup_hash": share_link_lookup_hash(links[1]["token"]),
            "ack_key": share_link_ack_key(links[1]["token"]),
        },
    )
    assert not_retrieved.status_code == 404

    # The raw token is not an accepted address: only its hash is.
    raw_token = custodian.post("/api/vault/share-links/retrieve", json={"lookup_hash": links[1]["token"]})
    assert raw_token.status_code == 400

    # === ADMIN ACCOUNT: created after the shares were handed out ===
    _register_admin_and_login(e2e_client)
    assert e2e_client.post("/api/vault/validate-setup", json={"setup_id": setup["setup_id"]}).status_code == 200

    # The setup did not wait for the custodians: two links are still pending.
    assert len(_share_link_rows(database_path)) == 2

    # Every custodian here comes from the same test client address, which
    # would otherwise exhaust the per-IP floor that link redemptions share.
    e2e_client.app.state.rate_limiter = InMemoryRateLimiter()

    # === VAULT LOCKED: links still deliver, they do not depend on the vault key ===
    assert e2e_client.post("/api/vault/lock").status_code == 200
    assert e2e_client.get("/api/vault/status").json()["status"] == "LOCKED"
    second_share = retrieve_share(custodian, links[1]["token"])
    acknowledge_share(custodian, links[1]["token"])

    # === UNLOCK with the shares the custodians collected ===
    unlock = custodian.post(
        "/api/vault/unlock", json={"unlock_session_id": "SHARELINKSESS001", "shares": [first_share, second_share]}
    )
    assert unlock.status_code == 200
    assert e2e_client.get("/api/vault/status").json()["status"] == "UNLOCKED"

    # === CSRF: a visitor who happens to be logged in still opens the public page ===
    # The page has no CSRF token in its store; the link is the only credential.
    e2e_client.disable_auto_csrf()
    third_share = retrieve_share(e2e_client, links[2]["token"])
    acknowledge_share(e2e_client, links[2]["token"])
    e2e_client.enable_auto_csrf()
    assert third_share.startswith("3:")
    assert _share_link_rows(database_path) == []

    # The listing is for administrators only: anonymous visitors, custodians included, get nothing.
    assert custodian.get("/api/vault/share-links").status_code == 401


def test_re_setup_kills_the_links_of_the_abandoned_attempt(e2e_client, client_factory):
    custodian = client_factory()

    first = e2e_client.post("/api/vault/setup", json={"nb_shares": 2, "threshold": 2}).json()
    second = e2e_client.post("/api/vault/setup", json={"nb_shares": 3, "threshold": 2}).json()

    stale = custodian.post(
        "/api/vault/share-links/retrieve",
        json={"lookup_hash": share_link_lookup_hash(first["share_links"][0]["token"])},
    )
    assert stale.status_code == 404

    # The new links work and their shares belong to the current master key.
    shares = [retrieve_share(custodian, link["token"]) for link in second["share_links"][:2]]
    _register_admin_and_login(e2e_client)
    assert e2e_client.post("/api/vault/validate-setup", json={"setup_id": second["setup_id"]}).status_code == 200
    assert e2e_client.post("/api/vault/lock").status_code == 200
    assert (
        custodian.post(
            "/api/vault/unlock", json={"unlock_session_id": "RESETUPSESSION01", "shares": shares}
        ).status_code
        == 200
    )


def test_sealed_share_is_useless_without_the_link(e2e_client, client_factory):
    """A database dump taken before retrieval holds ciphertexts nobody can open."""
    links = e2e_client.post("/api/vault/setup", json={"nb_shares": 2, "threshold": 2}).json()["share_links"]
    response = client_factory().post(
        "/api/vault/share-links/retrieve", json={"lookup_hash": share_link_lookup_hash(links[0]["token"])}
    )
    body = response.json()
    sealed, setup_id = body["sealed_share"], body["setup_id"]
    assert body["share_index"] == 1

    # Neither the lookup hash (stored) nor another link's token opens it.
    for wrong_key in (share_link_lookup_hash(links[0]["token"]), links[1]["token"]):
        with pytest.raises(InvalidTag):
            open_sealed_share(sealed, wrong_key, setup_id, 1)
    # Nor does relabelling it as another share
    with pytest.raises(InvalidTag):
        open_sealed_share(sealed, links[0]["token"], setup_id, 2)
    assert open_sealed_share(sealed, links[0]["token"], setup_id, 1).startswith("1:")


def _overview_links(client) -> dict[int, dict]:
    response = client.get("/api/vault/share-links")
    assert response.status_code == 200, response.text
    return {link["share_index"]: link for link in response.json()["links"]}


def test_admin_follows_the_share_links_without_ever_seeing_their_secrets(e2e_client, client_factory, database):
    custodian = client_factory()
    setup = e2e_client.post("/api/vault/setup", json={"nb_shares": 3, "threshold": 2}).json()
    links = setup["share_links"]
    _register_admin_and_login(e2e_client)

    pending = e2e_client.get("/api/vault/share-links")
    assert pending.status_code == 200
    assert pending.json()["setup_id"] == setup["setup_id"]
    assert (pending.json()["nb_shares"], pending.json()["threshold"]) == (3, 2)
    assert pending.json()["created_at"] is not None
    assert pending.json()["counts"] == {
        "pending": 3,
        "opened": 0,
        "opened_unconfirmed": 0,
        "acknowledged": 0,
        "expired": 0,
    }

    # Share 1 opened twice then confirmed, share 2 opened and left, share 3 untouched
    retrieve_share(custodian, links[0]["token"])
    assert _retrieve(custodian, links[0]["token"]).status_code == 200
    acknowledge_share(custodian, links[0]["token"])
    retrieve_share(custodian, links[1]["token"])

    # The rows are read before the response is judged: none of what they hold may leak
    rows = _share_link_rows(database)
    response = e2e_client.get("/api/vault/share-links")
    assert response.status_code == 200
    overview = response.json()
    by_index = {link["share_index"]: link for link in overview["links"]}

    assert [link["share_index"] for link in overview["links"]] == [1, 2, 3]
    assert [by_index[i]["status"] for i in (1, 2, 3)] == ["ACKNOWLEDGED", "OPENED", "PENDING"]
    assert by_index[1]["open_count"] == 2
    assert by_index[1]["acknowledged_at"] is not None and by_index[1]["first_opened_at"] is not None
    assert by_index[2]["open_count"] == 1 and by_index[2]["reopenable_until"] is not None
    assert by_index[3]["open_count"] == 0 and by_index[3]["first_opened_at"] is None
    assert overview["counts"] == {"pending": 1, "opened": 1, "opened_unconfirmed": 0, "acknowledged": 1, "expired": 0}

    forbidden_values = [link["token"] for link in links]
    for row in rows:
        forbidden_values += [row["lookup_hash"], row["ack_hash"], row["sealed_share"], str(row["id"])]
    forbidden_values += [share_link_lookup_hash(link["token"]) for link in links]
    assert len(forbidden_values) > 3
    for value in forbidden_values:
        assert value not in response.text
    for key in ("lookup_hash", "ack_hash", "sealed_share", "token", '"id"'):
        assert key not in response.text

    # Looking changes nothing: same answer twice, and the links keep their state
    assert e2e_client.get("/api/vault/share-links").json() == overview
    assert len(_share_link_rows(database)) == 2


def test_share_links_overview_ignores_the_events_of_an_abandoned_setup(e2e_client, client_factory):
    custodian = client_factory()
    first = e2e_client.post("/api/vault/setup", json={"nb_shares": 2, "threshold": 2}).json()
    retrieve_share(custodian, first["share_links"][0]["token"])
    acknowledge_share(custodian, first["share_links"][0]["token"])
    e2e_client.post("/api/vault/setup", json={"nb_shares": 3, "threshold": 2})
    _register_admin_and_login(e2e_client)

    links = _overview_links(e2e_client)

    assert sorted(links) == [1, 2, 3]
    assert {link["status"] for link in links.values()} == {"PENDING"}
    assert all(link["open_count"] == 0 and link["acknowledged_at"] is None for link in links.values())


def test_share_links_overview_requires_an_admin_and_a_vault(e2e_client, client_factory):
    anonymous = client_factory()
    assert anonymous.get("/api/vault/share-links").status_code == 401

    _register_admin_and_login(e2e_client)
    no_vault = e2e_client.get("/api/vault/share-links")
    assert no_vault.status_code == 404
    assert no_vault.json()["detail"]

    e2e_client.post("/api/vault/setup", json={"nb_shares": 2, "threshold": 2})
    created = e2e_client.post(
        "/api/users",
        json={
            "username": "plain@example.com",
            "email": "plain@example.com",
            "name": "Plain",
            "password": "securepassword123",
        },
    )
    assert created.status_code in (200, 201), created.text
    user = client_factory()
    assert (
        user.post("/api/auth/login", json={"email": "plain@example.com", "password": "securepassword123"}).status_code
        == 200
    )
    assert user.get("/api/vault/share-links").status_code == 403


def _pair_extension(client_factory, signed_in_client) -> str:
    """Run the real pairing flow for the signed-in user and return the bearer token."""
    verifier = "e2e-share-links-overview-verifier-that-is-long-enough"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    device = client_factory()
    registered = device.post(
        "/api/extension/device",
        json={"code_challenge": challenge, "code_challenge_method": "S256", "device_name": "Admin laptop"},
    )
    assert registered.status_code == 201, registered.text
    user_code = registered.json()["user_code"]
    assert signed_in_client.post(f"/api/extension/pairing/{user_code}/approve").status_code == 204
    exchanged = device.post("/api/extension/device/exchange", json={"user_code": user_code, "code_verifier": verifier})
    assert exchanged.status_code == 200, exchanged.text
    return exchanged.json()["token"]


def test_share_links_overview_rejects_an_extension_bearer_without_cookie(e2e_client, client_factory):
    _register_admin_and_login(e2e_client)
    e2e_client.post("/api/vault/setup", json={"nb_shares": 2, "threshold": 2})
    token = _pair_extension(client_factory, e2e_client)

    # Control: the paired token is valid, it is accepted by the extension's own route.
    bearer_only = client_factory()
    headers = {"Authorization": f"Bearer {token}"}
    assert bearer_only.get("/api/extension/session", headers=headers).status_code == 200

    # Admin routes read the session cookie only: a valid extension bearer alone is a 401.
    assert bearer_only.get("/api/vault/share-links", headers=headers).status_code == 401
