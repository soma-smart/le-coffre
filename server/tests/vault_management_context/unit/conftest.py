import pytest

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from .fakes import (
    FakeVaultRepository,
    FakeShamirGateway,
    FakeEncryptionGateway,
    FakeVaultSessionGateway,
    FakeShareRepository,
    FakeVaultEventRepository,
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


@pytest.fixture()
def share_repository():
    return FakeShareRepository()


@pytest.fixture()
def vault_event_repository():
    return FakeVaultEventRepository()


@pytest.fixture()
def event_publisher():
    return FakeDomainEventPublisher()
