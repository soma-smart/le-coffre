import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vault_management_context.domain.entities import Vault
from vault_management_context.adapters.primary.api.routes.vault_management_route import (
    router as vault_management_route,
)
from vault_management_context.adapters.primary.api.app_dependencies import (
    get_vault_repository,
    get_shamir_gateway,
)


@pytest.fixture
def client(vault_repository, shamir_gateway):
    app = FastAPI()
    app.include_router(vault_management_route)

    client = TestClient(app)

    client.app.dependency_overrides[get_vault_repository] = lambda: vault_repository
    client.app.dependency_overrides[get_shamir_gateway] = lambda: shamir_gateway

    return client


def test_can_create_the_vault(client, vault_repository, shamir_gateway):
    nb_shares = 5

    response = client.post(
        "/api/vault/setup",
        json={
            "nb_shares": nb_shares,
            "threshold": 3,
        },
    )

    assert response.status_code == 201

    generated_vault = vault_repository.get()
    for share in response.json()["shares"]:
        assert share["index"] in [s.index for s in generated_vault.shares]
        assert share["secret"] in [s.secret for s in generated_vault.shares]


def test_should_not_see_vault_when_vault_is_not_setup(client):
    response = client.head("/api/vault")

    assert response.status_code == 404


def test_should_see_vault_when_vault_is_setup(client, vault_repository):
    vault_repository.save(Vault(5, 3, []))

    response = client.head("/api/vault")

    assert response.status_code == 200
