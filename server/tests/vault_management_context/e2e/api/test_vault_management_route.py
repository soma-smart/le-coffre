import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.vault_management_context.domain.models import Vault
from src.vault_management_context.adapters.primary.api.routes import (
    vault_management_route,
)
from src.vault_management_context.adapters.primary.api.app_dependencies import (
    get_vault_repository,
    get_shamir_gateway,
)


@pytest.fixture
def client(vault_repository, shamir_gateway):
    app = FastAPI()
    app.include_router(vault_management_route.router)

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
    assert vault_repository.get() == Vault(nb_shares, 3, response.json()["shares"])


def test_should_not_see_vault_when_vault_is_not_setup(client):
    response = client.head("/api/vault")

    assert response.status_code == 404


def test_should_see_vault_when_vault_is_setup(client, vault_repository):
    vault_repository.save(Vault(5, 3, []))

    response = client.head("/api/vault")

    assert response.status_code == 200
