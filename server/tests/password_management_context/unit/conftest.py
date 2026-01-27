import pytest

from .fakes import (
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakeGroupAccessGateway,
    FakeEncryptionService,
)
from tests.fakes import FakeDomainEventPublisher


@pytest.fixture
def password_repository():
    return FakePasswordRepository()


@pytest.fixture
def encryption_service():
    return FakeEncryptionService()


@pytest.fixture
def password_permissions_repository():
    return FakePasswordPermissionsRepository()


@pytest.fixture
def group_access_gateway():
    return FakeGroupAccessGateway()


@pytest.fixture
def domain_event_publisher():
    return FakeDomainEventPublisher()
