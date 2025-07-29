import pytest

from src.vault_management_context.adapters.secondary.gateways.crypto_shamir_gateway import (
    CryptoShamirGateway,
)
from src.vault_management_context.adapters.secondary.gateways.fake_vault_repository import (
    FakeVaultRepository,
)


@pytest.fixture()
def vault_repository():
    return FakeVaultRepository()


@pytest.fixture()
def shamir_gateway():
    return CryptoShamirGateway()
