from datetime import UTC, datetime

import pytest

from tests.fakes import FakeDomainEventPublisher
from tests.shared_kernel.fakes.fake_time_gateway import FakeTimeGateway

from .fakes import (
    FakeGroupAccessGateway,
    FakeOneTimeLinkRepository,
    FakePasswordEncryptionGateway,
    FakePasswordEventRepository,
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakePasswordVaultAccessGateway,
)

# A fixed "now" so expiry-sensitive use cases are deterministic. Tests that care
# about a deadline move this clock rather than sleeping.
NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def time_gateway():
    return FakeTimeGateway(fixed_time=NOW)


@pytest.fixture
def password_repository():
    return FakePasswordRepository()


@pytest.fixture
def password_permissions_repository():
    return FakePasswordPermissionsRepository()


@pytest.fixture
def group_access_gateway():
    return FakeGroupAccessGateway()


@pytest.fixture
def domain_event_publisher():
    return FakeDomainEventPublisher()


@pytest.fixture
def password_encryption_gateway():
    return FakePasswordEncryptionGateway()


@pytest.fixture
def password_event_repository():
    return FakePasswordEventRepository()


@pytest.fixture
def password_vault_access_gateway():
    return FakePasswordVaultAccessGateway()


@pytest.fixture
def password_event_storage_service(password_event_repository):
    from password_management_context.application.services import (
        PasswordEventStorageService,
    )

    return PasswordEventStorageService(password_event_repository)


@pytest.fixture
def one_time_link_repository():
    return FakeOneTimeLinkRepository()


@pytest.fixture
def password_ownership_service(password_repository, password_permissions_repository, group_access_gateway):
    from password_management_context.application.services import PasswordOwnershipService

    return PasswordOwnershipService(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
    )
