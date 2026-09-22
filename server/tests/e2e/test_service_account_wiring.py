"""Smoke test that the service account endpoints are wired end to end.

The full lifecycle workflow lives in its own test; this one only proves the
routes, dependency providers and adapters resolve against a real database.
"""

import sqlite3

BASE = "/api/iam/service-accounts"


def test_the_service_account_endpoints_are_reachable(authenticated_admin_client, admin_personal_group_id, setup):
    client = authenticated_admin_client

    created = client.post(BASE, json={"group_id": str(admin_personal_group_id), "name": "nightly-backup"})
    assert created.status_code == 201, created.text
    account = created.json()
    assert account["token"]
    assert account["name"] == "nightly-backup"

    listed = client.get(BASE, params={"group_id": str(admin_personal_group_id)})
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()["items"]] == [account["id"]]
    assert account["token"] not in listed.text
    assert listed.json()["active"] == 1
    assert listed.json()["max_active"] == 3

    rotated = client.post(f"{BASE}/{account['id']}/rotate")
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["token"] != account["token"]

    revoked = client.delete(f"{BASE}/{account['id']}")
    assert revoked.status_code == 204, revoked.text

    after = client.get(BASE, params={"group_id": str(admin_personal_group_id)})
    assert after.json()["items"][0]["revoked_at"] is not None
    assert after.json()["active"] == 0


def test_listing_without_a_group_covers_every_reachable_group(
    authenticated_admin_client, admin_personal_group_id, setup
):
    client = authenticated_admin_client
    client.post(BASE, json={"group_id": str(admin_personal_group_id), "name": "unscoped"})

    response = client.get(BASE)

    assert response.status_code == 200, response.text
    assert "unscoped" in {item["name"] for item in response.json()["items"]}


def test_deleting_a_group_revokes_its_service_accounts(authenticated_admin_client, database_path, setup):
    client = authenticated_admin_client

    group = client.post("/api/groups/", json={"name": "doomed-team"})
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]

    created = client.post(BASE, json={"group_id": group_id, "name": "doomed-account"})
    assert created.status_code == 201, created.text
    account_id = created.json()["id"]

    deleted = client.delete(f"/api/groups/{group_id}")
    assert deleted.status_code in (200, 204), deleted.text

    # Asserted against the rows: with its group gone the account matches no
    # listing, so the database is the only place its fate is observable.
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            'SELECT revoked_at FROM "ServiceAccount" WHERE id = ?', (account_id.replace("-", ""),)
        ).fetchall()

    assert rows, "the account row must survive the group's deletion"
    assert rows[0][0] is not None, "the account must have been revoked"
