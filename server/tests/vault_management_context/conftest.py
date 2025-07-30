import pytest

from src.vault_management_context.adapters.secondary.gateways import (
    CryptoShamirGateway,
    FakeVaultRepository,
)

@pytest.fixture()
def vault_repository():
    return FakeVaultRepository()

@pytest.fixture()
def shamir_gateway():
    return CryptoShamirGateway()
