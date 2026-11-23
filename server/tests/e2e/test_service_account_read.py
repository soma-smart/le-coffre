"""A service account reads its group's secrets with its Bearer token, and nothing else."""

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute

from main import app
from password_management_context.adapters.primary.fastapi.app_dependencies import get_time_gateway
from tests.shared_kernel.fakes import FakeTimeGateway

SERVICE_ACCOUNTS = "/api/iam/service-accounts"
SECRET = "S3cr3t-for-the-CI"


@pytest.fixture
def deployments_group_id(authenticated_admin_client, setup) -> str:
    response = authenticated_admin_client.post("/api/groups/", json={"name": "Deployments"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def service_account(authenticated_admin_client, deployments_group_id) -> dict:
    response = authenticated_admin_client.post(
        SERVICE_ACCOUNTS, json={"group_id": deployments_group_id, "name": "nightly-deploy"}
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def bearer_client(unauthenticated_client, service_account):
    """A machine: no session cookie, only the token in a header."""
    unauthenticated_client.headers["Authorization"] = f"Bearer {service_account['token']}"
    return unauthenticated_client


def _create_password(client, group_id: str, name: str = "deploy-key") -> str:
    response = client.post("/api/passwords", json={"name": name, "password": SECRET, "group_id": group_id})
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ── whoami ───────────────────────────────────────────────────────────


def test_given_a_valid_token_when_asking_who_it_is_then_the_account_and_group_are_named(
    bearer_client, service_account, deployments_group_id
):
    response = bearer_client.get(f"{SERVICE_ACCOUNTS}/me")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "service_account_id": service_account["id"],
        "name": "nightly-deploy",
        "group_id": deployments_group_id,
        "group_name": "Deployments",
    }


def test_given_only_a_session_cookie_when_asking_who_it_is_then_it_is_refused(authenticated_admin_client, setup):
    response = authenticated_admin_client.get(f"{SERVICE_ACCOUNTS}/me")

    assert response.status_code == 401


def test_given_a_locked_vault_when_asking_who_it_is_then_the_token_still_answers(
    authenticated_admin_client, bearer_client
):
    assert authenticated_admin_client.post("/api/vault/lock").status_code == 200

    assert bearer_client.get(f"{SERVICE_ACCOUNTS}/me").status_code == 200


# ── Reading ──────────────────────────────────────────────────────────


def test_given_a_secret_of_its_group_when_reading_it_then_it_is_returned(
    authenticated_admin_client, bearer_client, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)

    response = bearer_client.get(f"/api/passwords/{password_id}")

    assert response.status_code == 200, response.text
    assert response.json() == {"password": SECRET}


def test_given_a_secret_shared_with_its_group_when_reading_it_then_it_is_returned(
    authenticated_admin_client, bearer_client, deployments_group_id, admin_personal_group_id
):
    password_id = _create_password(authenticated_admin_client, admin_personal_group_id)
    share = authenticated_admin_client.post(
        f"/api/passwords/{password_id}/share", json={"group_id": deployments_group_id}
    )
    assert share.status_code in (200, 201), share.text

    assert bearer_client.get(f"/api/passwords/{password_id}").json() == {"password": SECRET}


def test_given_a_secret_outside_its_scope_when_reading_it_then_it_looks_like_it_does_not_exist(
    authenticated_admin_client, bearer_client, admin_personal_group_id
):
    out_of_scope_id = _create_password(authenticated_admin_client, admin_personal_group_id)

    out_of_scope = bearer_client.get(f"/api/passwords/{out_of_scope_id}")
    nonexistent = bearer_client.get(f"/api/passwords/{uuid4()}")

    assert out_of_scope.status_code == nonexistent.status_code == 404
    assert out_of_scope.json() == nonexistent.json() == {"detail": "Password not found"}


def test_given_a_share_that_expired_when_reading_it_then_it_is_refused(
    authenticated_admin_client, bearer_client, deployments_group_id, admin_personal_group_id
):
    password_id = _create_password(authenticated_admin_client, admin_personal_group_id)
    in_one_hour = datetime.now(UTC) + timedelta(hours=1)
    share = authenticated_admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": deployments_group_id, "expires_at": in_one_hour.isoformat()},
    )
    assert share.status_code in (200, 201), share.text
    assert bearer_client.get(f"/api/passwords/{password_id}").status_code == 200

    app.dependency_overrides[get_time_gateway] = lambda: FakeTimeGateway(in_one_hour + timedelta(minutes=1))
    try:
        response = bearer_client.get(f"/api/passwords/{password_id}")
    finally:
        app.dependency_overrides.pop(get_time_gateway)

    assert response.status_code == 404
    assert response.json() == {"detail": "Password not found"}


def test_given_a_locked_vault_when_reading_then_it_answers_503_not_a_denial(
    authenticated_admin_client, bearer_client, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)
    assert authenticated_admin_client.post("/api/vault/lock").status_code == 200

    response = bearer_client.get(f"/api/passwords/{password_id}")

    assert response.status_code == 503
    assert "locked" in response.json()["detail"].lower()


def test_given_a_locked_vault_when_reading_a_secret_outside_its_scope_then_existence_is_still_hidden(
    authenticated_admin_client, bearer_client, admin_personal_group_id
):
    """The scope is checked before the vault: a locked vault must not become an existence oracle."""
    out_of_scope_id = _create_password(authenticated_admin_client, admin_personal_group_id)
    assert authenticated_admin_client.post("/api/vault/lock").status_code == 200

    assert bearer_client.get(f"/api/passwords/{out_of_scope_id}").status_code == 404


def test_given_a_locked_vault_when_reading_with_an_unusable_token_then_it_answers_401_not_503(
    authenticated_admin_client, unauthenticated_client, deployments_group_id
):
    """The token is checked before the vault: a locked vault must not tell a bad token from a good one."""
    password_id = _create_password(authenticated_admin_client, deployments_group_id)
    assert authenticated_admin_client.post("/api/vault/lock").status_code == 200
    unauthenticated_client.headers["Authorization"] = "Bearer " + "A" * 43

    response = unauthenticated_client.get(f"/api/passwords/{password_id}")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_given_a_read_when_listing_the_secret_history_then_the_service_account_is_the_actor(
    authenticated_admin_client, bearer_client, service_account, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)

    bearer_client.get(f"/api/passwords/{password_id}")

    events = authenticated_admin_client.get(f"/api/passwords/{password_id}/events").json()["events"]
    (accessed,) = [event for event in events if event["event_type"] == "PasswordAccessedEvent"]
    assert accessed["actor_principal_id"] == service_account["id"]
    assert accessed["actor"] == {"kind": "service_account", "display_name": "nightly-deploy"}


# ── Refused tokens ───────────────────────────────────────────────────


def test_given_a_regenerated_token_when_reading_with_the_old_one_then_it_is_refused(
    authenticated_admin_client, bearer_client, service_account, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)
    rotated = authenticated_admin_client.post(f"{SERVICE_ACCOUNTS}/{service_account['id']}/rotate")
    assert rotated.status_code == 200, rotated.text

    old = bearer_client.get(f"/api/passwords/{password_id}")
    bearer_client.headers["Authorization"] = f"Bearer {rotated.json()['token']}"
    new = bearer_client.get(f"/api/passwords/{password_id}")

    assert old.status_code == 401
    assert new.status_code == 200


def test_given_a_revoked_account_when_reading_then_it_is_refused(
    authenticated_admin_client, bearer_client, service_account, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)
    assert authenticated_admin_client.delete(f"{SERVICE_ACCOUNTS}/{service_account['id']}").status_code in (200, 204)

    response = bearer_client.get(f"/api/passwords/{password_id}")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "authorization",
    [
        pytest.param("Bearer not-a-token", id="malformed"),
        pytest.param("Bearer " + "A" * 43, id="unknown"),
        pytest.param("Basic dXNlcjpwYXNz", id="wrong-scheme"),
    ],
)
def test_given_an_unusable_token_when_reading_then_it_is_refused(
    authenticated_admin_client, unauthenticated_client, deployments_group_id, authorization
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)
    unauthenticated_client.headers["Authorization"] = authorization

    response = unauthenticated_client.get(f"/api/passwords/{password_id}")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_given_a_human_session_when_reading_then_nothing_changed_for_humans(
    authenticated_admin_client, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)

    assert authenticated_admin_client.get(f"/api/passwords/{password_id}").json() == {"password": SECRET}


# ── Extension routes ─────────────────────────────────────────────────


@pytest.mark.parametrize("path", ["/api/extension/groups", "/api/extension/session"])
def test_given_a_service_account_token_when_calling_an_extension_route_then_it_is_refused(bearer_client, path):
    response = bearer_client.get(path)

    assert response.status_code == 403


def test_given_a_service_account_id_when_an_admin_disconnects_its_extensions_then_its_token_still_works(
    authenticated_admin_client, bearer_client, service_account
):
    """The admin route cuts a user's extensions only: it must not leave an active account without its token."""
    response = authenticated_admin_client.delete(f"/api/admin/users/{service_account['id']}/extension-tokens")

    assert response.status_code == 200, response.text
    assert response.json() == {"revoked_count": 0}
    assert bearer_client.get(f"{SERVICE_ACCOUNTS}/me").status_code == 200


def test_given_a_service_account_id_when_an_admin_deletes_it_as_a_user_then_its_token_still_works(
    authenticated_admin_client, bearer_client, service_account
):
    """The user deletion route answers 404 for it, and must not cut its token on the way."""
    response = authenticated_admin_client.delete(f"/api/users/{service_account['id']}")

    assert response.status_code == 404, response.text
    assert bearer_client.get(f"{SERVICE_ACCOUNTS}/me").status_code == 200


# ── Every other route ────────────────────────────────────────────────

# The only routes a service account may succeed on. Everything else is refused by
# default, and the two tests below check it on every route the application
# declares, so a new route is covered without anyone adding it here.
ALLOWED_TO_A_SERVICE_ACCOUNT = {("GET", "/passwords/{password_id}"), ("GET", "/iam/service-accounts/me")}


def _api_routes(routes):
    # Included routers stay wrapped, their routes hang off original_router.
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        included = getattr(route, "original_router", None)
        if included is not None:
            yield from _api_routes(included.routes)


def _declared(methods: set[str]) -> list[tuple[str, str]]:
    declared = sorted({(method, route.path) for route in _api_routes(app.routes) for method in route.methods & methods})
    assert declared, "no route found: the route listing no longer matches FastAPI's shape"
    return declared


def _call(client, method: str, path: str):
    # A random id fills each path parameter, so only the authentication layer decides.
    url = "/api" + re.sub(r"\{[^}]+\}", str(uuid4()), path)
    return client.request(method, url, follow_redirects=False)


def test_given_a_service_account_token_when_calling_any_mutating_route_then_it_is_refused(bearer_client):
    accepted = [
        (method, path, response.status_code)
        for method, path in _declared({"POST", "PUT", "PATCH", "DELETE"})
        if (response := _call(bearer_client, method, path)).status_code != 403
    ]

    assert accepted == []


def test_given_a_service_account_token_when_reading_any_other_route_then_it_gets_no_more_than_an_anonymous_caller(
    bearer_client, client_factory
):
    """Refused outright (401 or 403), or answered exactly as anyone, as a public route is.

    A 404 does not count as a refusal: with a random id, a route serving the token
    a resource would answer 404 too.
    """
    anonymous = client_factory()
    granted = []
    for method, path in _declared({"GET"}):
        if (method, path) in ALLOWED_TO_A_SERVICE_ACCOUNT:
            continue
        with_token = _call(bearer_client, method, path).status_code
        without = _call(anonymous, method, path).status_code
        if with_token not in (401, 403) and with_token != without:
            granted.append((method, path, with_token, without))

    assert granted == []


# ── Last use ─────────────────────────────────────────────────────────


def _listed(client, group_id: str, account_id: str) -> dict:
    response = client.get(SERVICE_ACCOUNTS, params={"group_id": group_id})
    assert response.status_code == 200, response.text
    return next(item for item in response.json()["items"] if item["id"] == account_id)


def test_given_a_read_when_listing_then_the_owner_sees_when_the_account_was_last_used(
    authenticated_admin_client, bearer_client, service_account, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)
    new = _listed(authenticated_admin_client, deployments_group_id, service_account["id"])
    assert (new["last_used_at"], new["last_rotated_at"]) == (None, None)
    before = datetime.now(UTC)

    assert bearer_client.get(f"/api/passwords/{password_id}").status_code == 200

    listed = _listed(authenticated_admin_client, deployments_group_id, service_account["id"])
    assert listed["last_used_at"] is not None
    assert datetime.fromisoformat(listed["last_used_at"]) >= before - timedelta(seconds=1)


def test_given_a_rotation_when_the_new_token_reads_then_its_use_is_dated_after_the_rotation(
    authenticated_admin_client, bearer_client, service_account, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)
    assert bearer_client.get(f"/api/passwords/{password_id}").status_code == 200
    rotated = authenticated_admin_client.post(f"{SERVICE_ACCOUNTS}/{service_account['id']}/rotate")
    assert rotated.status_code == 200, rotated.text
    after_rotation = _listed(authenticated_admin_client, deployments_group_id, service_account["id"])
    assert after_rotation["last_rotated_at"] is not None
    assert datetime.fromisoformat(after_rotation["last_used_at"]) < datetime.fromisoformat(
        after_rotation["last_rotated_at"]
    ), "the new token is not used yet"

    # Within the coarsening window of the old token's use: the new token's first use still shows.
    bearer_client.headers["Authorization"] = f"Bearer {rotated.json()['token']}"
    assert bearer_client.get(f"/api/passwords/{password_id}").status_code == 200

    listed = _listed(authenticated_admin_client, deployments_group_id, service_account["id"])
    assert datetime.fromisoformat(listed["last_used_at"]) >= datetime.fromisoformat(listed["last_rotated_at"])


def test_given_a_revoked_account_when_listing_then_its_last_use_is_kept(
    authenticated_admin_client, bearer_client, service_account, deployments_group_id
):
    password_id = _create_password(authenticated_admin_client, deployments_group_id)
    assert bearer_client.get(f"/api/passwords/{password_id}").status_code == 200
    used_at = _listed(authenticated_admin_client, deployments_group_id, service_account["id"])["last_used_at"]

    assert authenticated_admin_client.delete(f"{SERVICE_ACCOUNTS}/{service_account['id']}").status_code in (200, 204)

    listed = _listed(authenticated_admin_client, deployments_group_id, service_account["id"])
    assert listed["revoked_at"] is not None
    assert listed["last_used_at"] == used_at
