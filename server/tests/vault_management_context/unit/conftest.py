import pytest

from vault_management_context.adapters.secondary.gateways import (
    InMemoryVaultSessionGateway,
)
from .mocks import (
    FakeVaultRepository,
    FakeShamirGateway,
    FakeEncryptionGateway,
)


@pytest.fixture()
def vault_repository():
    return FakeVaultRepository()


@pytest.fixture()
def shamir_gateway():
    return FakeShamirGateway()


@pytest.fixture()
def encryption_gateway():
    return FakeEncryptionGateway()


@pytest.fixture()
def vault_session_gateway():
    return InMemoryVaultSessionGateway()
