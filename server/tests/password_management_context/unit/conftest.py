import pytest

from password_management_context.adapters.secondary import (
    InMemoryPasswordRepository,
)
from identity_access_management_context.adapters.secondary import (
    InMemoryUserRepository,
)
from password_management_context.application.services import PasswordAccessService
from .fakes import FakeEncryptionService
from .fakes.fake_password_permissions_repository import (
    FakePasswordPermissionsRepository,
)
from .fakes.fake_group_access_gateway import FakeGroupAccessGateway
from tests.fakes import FakeDomainEventPublisher


@pytest.fixture
def password_repository():
    return InMemoryPasswordRepository()


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
def user_repository():
    return InMemoryUserRepository()


@pytest.fixture
def event_publisher():
    return FakeDomainEventPublisher()


@pytest.fixture
def password_access_service(password_permissions_repository, group_access_gateway):
    return PasswordAccessService(password_permissions_repository, group_access_gateway)
