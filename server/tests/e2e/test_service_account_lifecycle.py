"""A group owner manages its service accounts: who may, how many, and what the group history keeps."""

import pytest

from tests.e2e.conftest import get_personal_group_id

SERVICE_ACCOUNTS = "/api/iam/service-accounts"


@pytest.fixture
def team_group_id(authenticated_admin_client, setup) -> str:
    response = authenticated_admin_client.post("/api/groups/", json={"name": "Platform"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def member_client(authenticated_admin_client, client_factory, team_group_id):
    """A plain member of the team group: not one of its owners."""
    email, password = "member@example.com", "SecurePassword123!"
    created = authenticated_admin_client.post(
        "/api/users", json={"username": "member", "email": email, "name": "Member", "password": password}
    )
    assert created.status_code in (200, 201), created.text
    added = authenticated_admin_client.post(
        f"/api/groups/{team_group_id}/members", json={"user_id": created.json()["id"]}
    )
    assert added.status_code in (200, 201, 204), added.text

    client = client_factory()
    assert client.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200
    return client


def _create(client, group_id, name="nightly-deploy"):
    return client.post(SERVICE_ACCOUNTS, json={"group_id": str(group_id), "name": name})


def test_given_a_plain_member_when_creating_rotating_or_revoking_then_each_is_refused(
    authenticated_admin_client, member_client, client_factory, team_group_id
):
    created = _create(authenticated_admin_client, team_group_id)
    assert created.status_code == 201, created.text
    account = created.json()

    assert _create(member_client, team_group_id, name="sneaky").status_code == 403
    assert member_client.post(f"{SERVICE_ACCOUNTS}/{account['id']}/rotate").status_code == 403
    assert member_client.delete(f"{SERVICE_ACCOUNTS}/{account['id']}").status_code == 403

    # Nothing changed: the owner's token still proves the account.
    bearer = client_factory()
    me = bearer.get(f"{SERVICE_ACCOUNTS}/me", headers={"Authorization": f"Bearer {account['token']}"})
    assert me.status_code == 200, me.text
    listed = authenticated_admin_client.get(SERVICE_ACCOUNTS, params={"group_id": team_group_id}).json()
    assert [item["name"] for item in listed["items"]] == ["nightly-deploy"]


def test_given_the_cap_is_reached_when_creating_then_it_is_refused_until_one_is_revoked(
    authenticated_admin_client, team_group_id, monkeypatch
):
    monkeypatch.setenv("MAX_ACTIVE_SERVICE_ACCOUNTS_PER_GROUP", "2")
    first = _create(authenticated_admin_client, team_group_id, name="first")
    assert first.status_code == 201, first.text
    assert _create(authenticated_admin_client, team_group_id, name="second").status_code == 201

    refused = _create(authenticated_admin_client, team_group_id, name="third")

    assert refused.status_code == 409
    assert "maximum 2" in refused.json()["detail"]

    assert authenticated_admin_client.delete(f"{SERVICE_ACCOUNTS}/{first.json()['id']}").status_code == 204
    assert _create(authenticated_admin_client, team_group_id, name="third").status_code == 201


def test_given_a_lifecycle_on_a_personal_group_when_reading_its_history_then_each_change_shows_without_the_token(
    authenticated_admin_client, setup
):
    client = authenticated_admin_client
    personal_group_id = get_personal_group_id(client)

    created = _create(client, personal_group_id)
    assert created.status_code == 201, created.text
    account = created.json()
    rotated = client.post(f"{SERVICE_ACCOUNTS}/{account['id']}/rotate")
    assert rotated.status_code == 200, rotated.text
    assert client.delete(f"{SERVICE_ACCOUNTS}/{account['id']}").status_code == 204
    # Opening the dialog lists the accounts: a read, which the history leaves out.
    assert client.get(SERVICE_ACCOUNTS, params={"group_id": str(personal_group_id)}).status_code == 200

    history = client.get(f"/api/groups/{personal_group_id}/events")

    assert history.status_code == 200, history.text
    events = history.json()["events"]
    assert [event["event_type"] for event in events] == [
        "ServiceAccountRevokedEvent",
        "ServiceAccountTokenRotatedEvent",
        "ServiceAccountCreatedEvent",
    ]
    for event in events:
        assert event["event_data"]["service_account_id"] == account["id"]
        assert event["event_data"]["service_account_name"] == "nightly-deploy"
        assert event["actor"]["kind"] == "user"
        assert event["actor"]["display_name"]
    assert account["token"] not in history.text
    assert rotated.json()["token"] not in history.text
