import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import List

from vault_management_context.domain.entities import Share
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
    nb_shares = 3
    expected_shares: List[Share] = [Share(0, "1"), Share(1, "2"), Share(2, "3")]
    shamir_gateway.set(expected_shares)

    response = client.post(
        "/api/vault/setup",
        json={
            "nb_shares": nb_shares,
            "threshold": 3,
        },
    )

    assert response.status_code == 201

    response_data = response.json()
    assert response_data["shares"] == [share.to_dict() for share in expected_shares]

    generated_vault = vault_repository.get()
    assert generated_vault.nb_shares == nb_shares
    assert generated_vault.threshold == 3
