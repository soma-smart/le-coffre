"""Smoke test that the service account endpoints are wired end to end.

The full lifecycle workflow lives in its own test; this one only proves the
routes, dependency providers and adapters resolve against a real database.
"""

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

    rotated = client.post(f"{BASE}/{account['id']}/rotate")
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["token"] != account["token"]

    revoked = client.delete(f"{BASE}/{account['id']}")
    assert revoked.status_code == 204, revoked.text

    after = client.get(BASE, params={"group_id": str(admin_personal_group_id)})
    assert after.json()["items"][0]["revoked_at"] is not None


def test_listing_without_a_group_is_refused(authenticated_admin_client, setup):
    """An absent filter must not fall back to every group's accounts."""
    response = authenticated_admin_client.get(BASE)

    assert response.status_code == 422
