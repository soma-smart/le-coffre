import pytest

from mocks.adapters.secondary import (
    FakeVaultRepository,
    FakeShamirGateway,
    FakeEncryptionGateway,
    FakeVaultSessionGateway,
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
    return FakeVaultSessionGateway()
