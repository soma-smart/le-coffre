import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.vault_management_context.business_logic.models.value_objects.vault import Vault
from src.vault_management_context.adapters.primary.api.routes import (
    vault_management_route,
)
from src.vault_management_context.adapters.primary.api.app_dependencies import (
    get_vault_repository,
    get_shamir_gateway,
)
from tests.vault_management_context.fixtures import vault_repository, shamir_gateway


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(vault_management_route.router)

    return TestClient(app)


def test_can_create_the_vault(client, vault_repository, shamir_gateway):
    nb_shares = 5

    client.app.dependency_overrides[get_vault_repository] = lambda: vault_repository
    client.app.dependency_overrides[get_shamir_gateway] = lambda: shamir_gateway

    response = client.post(
        "/vault",
        json={
            "nb_shares": nb_shares,
            "threshold": 3,
        },
    )

    assert response.status_code == 201
    assert vault_repository.get() == Vault(nb_shares, 3, response.json()["shares"])
