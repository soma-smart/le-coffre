import pytest

from user_management_context.adapters.secondary.gateways import (
    InMemoryUserRepository,
)
from .mocks.fake_hash_password_service import FakeHashPasswordService


@pytest.fixture
def user_repository():
    return InMemoryUserRepository()


@pytest.fixture
def hash_password_service():
    return FakeHashPasswordService()
