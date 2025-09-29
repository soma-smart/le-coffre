import pytest

from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from .mocks import FakeEncryptionService
from tests.mocks.fake_access_controller import (
    FakeAccessController,
)


@pytest.fixture
def password_repository():
    return InMemoryPasswordRepository()


@pytest.fixture
def encryption_service():
    return FakeEncryptionService()


@pytest.fixture
def access_controller():
    return FakeAccessController()
