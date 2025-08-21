import pytest

from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from .mocks import FakeEncryptionService


@pytest.fixture
def password_repository():
    return InMemoryPasswordRepository()


@pytest.fixture
def encryption_service():
    return FakeEncryptionService()
