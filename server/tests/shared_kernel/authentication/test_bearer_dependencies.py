from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from starlette.testclient import TestClient

from identity_access_management_context.application.responses import ValidateUserTokenResponse
from identity_access_management_context.application.services.authentication import TokenAuthenticator
from identity_access_management_context.application.use_cases import (
    AuthenticateTokenUseCase,
    ValidateUserTokenUseCase,
)
from identity_access_management_context.domain.entities import ServiceAccount, TokenCredentialRecord
from identity_access_management_context.domain.exceptions import InvalidTokenException
from identity_access_management_context.domain.value_objects import TokenCredential
from shared_kernel.adapters.primary.dependencies import (
    get_authenticate_token_usecase,
    get_current_principal,
    get_current_service_account,
    get_validate_token_usecase,
)
from shared_kernel.domain.entities import AuthenticatedPrincipal
from tests.identity_access_management_context.unit.fakes import (
    FakePrincipalRepository,
    FakeServiceAccountRepository,
    FakeTokenCredentialRecordRepository,
    FakeUserRepository,
)
from tests.shared_kernel.fakes import FakeTimeGateway

GROUP_ID = UUID("00000000-0000-0000-0000-0000000000b1")
USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
VALID_COOKIE = "valid-session-cookie"


@pytest.fixture
def service_account_and_token():
    account = ServiceAccount.create(group_id=GROUP_ID, name="nightly-backup")
    return account, TokenCredential.generate()


@pytest.fixture
def client(service_account_and_token):
    account, token = service_account_and_token
    service_account_repository = FakeServiceAccountRepository()
    service_account_repository.create([account])
    token_credential_record_repository = FakeTokenCredentialRecordRepository()
    token_credential_record_repository.create([TokenCredentialRecord(principal_id=account.id, token_hash=token.hash)])
    time_provider = FakeTimeGateway()
    authenticate_usecase = AuthenticateTokenUseCase(
        TokenAuthenticator(
            principal_repository=FakePrincipalRepository(FakeUserRepository(), service_account_repository),
            token_credential_record_repository=token_credential_record_repository,
            time_provider=time_provider,
        ),
        token_credential_record_repository,
        time_provider,
        300,
    )

    def validate(command):
        if command.jwt_token != VALID_COOKIE:
            raise InvalidTokenException()
        return ValidateUserTokenResponse(
            is_valid=True, user_id=USER_ID, email="alice@example.com", display_name="Alice", roles=[]
        )

    validate_usecase = Mock(spec=ValidateUserTokenUseCase)
    validate_usecase.execute = Mock(side_effect=validate)

    app = FastAPI()

    @app.get("/machine-only")
    def machine_only(service_account: AuthenticatedPrincipal = Depends(get_current_service_account)):
        return {"id": str(service_account.principal_id), "kind": service_account.kind}

    @app.get("/humans-and-machines")
    def humans_and_machines(principal: AuthenticatedPrincipal = Depends(get_current_principal)):
        return {"id": str(principal.principal_id), "kind": principal.kind}

    app.dependency_overrides[get_authenticate_token_usecase] = lambda: authenticate_usecase
    app.dependency_overrides[get_validate_token_usecase] = lambda: validate_usecase
    return TestClient(app)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── get_current_service_account ──────────────────────────────────────


def test_given_a_valid_token_when_calling_a_machine_only_route_should_resolve_the_service_account(
    client, service_account_and_token
):
    account, token = service_account_and_token

    response = client.get("/machine-only", headers=_bearer(token.value))

    assert response.status_code == 200
    assert response.json() == {"id": str(account.id), "kind": "service_account"}


@pytest.mark.parametrize("scheme", ["Bearer", "bearer", "BEARER"])
def test_given_any_casing_of_the_bearer_scheme_when_calling_should_accept_the_token(
    client, service_account_and_token, scheme
):
    _, token = service_account_and_token

    response = client.get("/machine-only", headers={"Authorization": f"{scheme} {token.value}"})

    assert response.status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="missing"),
        pytest.param({"Authorization": "Bearer"}, id="empty"),
        pytest.param({"Authorization": "Bearer short"}, id="malformed"),
        pytest.param({"Authorization": f"Basic {TokenCredential.generate().value}"}, id="wrong-scheme"),
        pytest.param(_bearer(TokenCredential.generate().value), id="unknown"),
    ],
)
def test_given_an_unusable_token_when_calling_a_machine_only_route_should_answer_the_same_401(client, headers):
    response = client.get("/machine-only", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_given_only_a_session_cookie_when_calling_a_machine_only_route_should_refuse(client):
    client.cookies.set("access_token", VALID_COOKIE)

    response = client.get("/machine-only")

    assert response.status_code == 401


# ── get_current_principal ────────────────────────────────────────────


def test_given_a_valid_token_when_calling_a_shared_route_should_resolve_a_service_account(
    client, service_account_and_token
):
    account, token = service_account_and_token

    response = client.get("/humans-and-machines", headers=_bearer(token.value))

    assert response.status_code == 200
    assert response.json() == {"id": str(account.id), "kind": "service_account"}


def test_given_a_valid_cookie_when_calling_a_shared_route_should_resolve_a_user(client):
    client.cookies.set("access_token", VALID_COOKIE)

    response = client.get("/humans-and-machines")

    assert response.status_code == 200
    assert response.json() == {"id": str(USER_ID), "kind": "user"}


def test_given_neither_cookie_nor_token_when_calling_a_shared_route_should_refuse(client):
    response = client.get("/humans-and-machines")

    assert response.status_code == 401


def test_given_a_valid_cookie_and_a_bad_token_when_calling_a_shared_route_should_resolve_the_user(client):
    """The cookie wins: a token is only looked at when no session cookie is presented."""
    client.cookies.set("access_token", VALID_COOKIE)

    response = client.get("/humans-and-machines", headers=_bearer(TokenCredential.generate().value))

    assert response.json() == {"id": str(USER_ID), "kind": "user"}


def test_given_an_invalid_cookie_and_a_valid_token_when_calling_a_shared_route_should_not_fall_back_to_the_token(
    client, service_account_and_token
):
    """A bad cookie is fatal: a token must not rescue an expired session."""
    _, token = service_account_and_token
    client.cookies.set("access_token", "expired-cookie")

    response = client.get("/humans-and-machines", headers=_bearer(token.value))

    assert response.status_code == 401
