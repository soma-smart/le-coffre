import pytest

from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from .mocks import FakeEncryptionService
from tests.mocks import FakeAccessController, FakeDomainEventPublisher


@pytest.fixture
def password_repository():
    return InMemoryPasswordRepository()


@pytest.fixture
def encryption_service():
    return FakeEncryptionService()


@pytest.fixture
def access_controller():
    return FakeAccessController()


@pytest.fixture
def domain_event_publisher():
    return FakeDomainEventPublisher()
