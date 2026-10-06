from datetime import UTC, datetime

import pytest

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from tests.shared_kernel.fakes.fake_time_gateway import FakeTimeGateway

from .fakes import (
    FakeEncryptionGateway,
    FakeShamirGateway,
    FakeShareLinkRepository,
    FakeShareRepository,
    FakeShareSealingGateway,
    FakeVaultEventRepository,
    FakeVaultRepository,
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


@pytest.fixture()
def share_repository():
    return FakeShareRepository()


@pytest.fixture()
def vault_event_repository():
    return FakeVaultEventRepository()


@pytest.fixture()
def event_publisher():
    return FakeDomainEventPublisher()


@pytest.fixture()
def share_link_repository():
    return FakeShareLinkRepository()


@pytest.fixture()
def share_sealing_gateway():
    return FakeShareSealingGateway()


@pytest.fixture()
def time_gateway():
    return FakeTimeGateway(datetime(2026, 10, 6, 9, 0, tzinfo=UTC))
