import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vault_management_context.adapters.primary.api.routes import (
    get_vault_management_router,
)
from vault_management_context.adapters.primary.api.app_dependencies import (
    get_vault_repository,
    get_shamir_gateway,
    get_encryption_gateway,
    get_vault_session_gateway,
)
from vault_management_context.adapters.secondary.gateways import (
    InMemoryVaultRepository,
    CryptoShamirGateway,
    AesEncryptionGateway,
    InMemoryVaultSessionGateway,
)


@pytest.fixture
def vault_repository():
    return InMemoryVaultRepository()


@pytest.fixture
def shamir_gateway():
    return CryptoShamirGateway()


@pytest.fixture
def encryption_gateway():
    return AesEncryptionGateway()


@pytest.fixture
def vault_session_gateway():
    return InMemoryVaultSessionGateway()


@pytest.fixture
def e2e_client(
    vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway
):
    app = FastAPI()
    app.include_router(get_vault_management_router())

    client = TestClient(app)

    client.app.dependency_overrides[get_vault_repository] = lambda: vault_repository
    client.app.dependency_overrides[get_shamir_gateway] = lambda: shamir_gateway
    client.app.dependency_overrides[get_encryption_gateway] = lambda: encryption_gateway
    client.app.dependency_overrides[get_vault_session_gateway] = (
        lambda: vault_session_gateway
    )
    return client
