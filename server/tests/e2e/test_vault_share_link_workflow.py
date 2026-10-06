"""
End-to-end test for the links distributing the Shamir shares at vault setup.

Covers:
- setup hands out one link per share and never a share in clear
- a custodian with no account retrieves their share once, and only once
- what the database holds can neither reveal a share nor rebuild the master key
- links keep working while the vault is locked (when the shares are needed)
- a re-setup kills the links of the abandoned attempt
- the retrieved shares unlock the vault
"""

import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import create_engine, text

from tests.vault_management_context.share_link_crypto import open_sealed_share, retrieve_share, share_link_lookup_hash

UNUSABLE_DETAIL = "This share link is invalid, expired or has already been used"


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
        assert link["token"] not in str(row)
        assert row["sealed_share"]

    # === RETRIEVE: anonymous, no CSRF token, no session ===
    first_share = retrieve_share(custodian, links[0]["token"])
    assert first_share.startswith("1:")

    # Once retrieved, nothing of the link is left in the database.
    assert sorted(row["share_index"] for row in _share_link_rows(database_path)) == [2, 3]

    # === SINGLE USE: a second retrieval gets the same answer as an unknown link ===
    replay = custodian.post(
        "/api/vault/share-links/retrieve", json={"lookup_hash": share_link_lookup_hash(links[0]["token"])}
    )
    unknown = custodian.post(
        "/api/vault/share-links/retrieve", json={"lookup_hash": share_link_lookup_hash("never-issued")}
    )
    assert replay.status_code == unknown.status_code == 404
    assert replay.json() == unknown.json() == {"detail": UNUSABLE_DETAIL}

    # The raw token is not an accepted address: only its hash is.
    raw_token = custodian.post("/api/vault/share-links/retrieve", json={"lookup_hash": links[1]["token"]})
    assert raw_token.status_code == 400

    # === ADMIN ACCOUNT: created after the shares were handed out ===
    _register_admin_and_login(e2e_client)
    assert e2e_client.post("/api/vault/validate-setup", json={"setup_id": setup["setup_id"]}).status_code == 200

    # The setup did not wait for the custodians: two links are still pending.
    assert len(_share_link_rows(database_path)) == 2

    # === VAULT LOCKED: links still deliver, they do not depend on the vault key ===
    assert e2e_client.post("/api/vault/lock").status_code == 200
    assert e2e_client.get("/api/vault/status").json()["status"] == "LOCKED"
    second_share = retrieve_share(custodian, links[1]["token"])

    # === UNLOCK with the shares the custodians collected ===
    unlock = custodian.post("/api/vault/unlock", json={"shares": [first_share, second_share]})
    assert unlock.status_code == 200
    assert e2e_client.get("/api/vault/status").json()["status"] == "UNLOCKED"

    # === CSRF: a visitor who happens to be logged in still opens the public page ===
    # The page has no CSRF token in its store; the link is the only credential.
    e2e_client.disable_auto_csrf()
    third_share = retrieve_share(e2e_client, links[2]["token"])
    e2e_client.enable_auto_csrf()
    assert third_share.startswith("3:")
    assert _share_link_rows(database_path) == []

    # No listing of the links is exposed, to anyone.
    assert e2e_client.get("/api/vault/share-links").status_code in (404, 405)


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
    assert custodian.post("/api/vault/unlock", json={"shares": shares}).status_code == 200


def test_sealed_share_is_useless_without_the_link(e2e_client, client_factory):
    """A database dump taken before retrieval holds ciphertexts nobody can open."""
    links = e2e_client.post("/api/vault/setup", json={"nb_shares": 2, "threshold": 2}).json()["share_links"]
    response = client_factory().post(
        "/api/vault/share-links/retrieve", json={"lookup_hash": share_link_lookup_hash(links[0]["token"])}
    )
    sealed = response.json()["sealed_share"]

    # Neither the lookup hash (stored) nor another link's token opens it.
    for wrong_key in (share_link_lookup_hash(links[0]["token"]), links[1]["token"]):
        with pytest.raises(InvalidTag):
            open_sealed_share(sealed, wrong_key)
    assert open_sealed_share(sealed, links[0]["token"]).startswith("1:")
