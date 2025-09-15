import pytest

from user_management_context.adapters.output.interfaces import (
    InMemoryUserRepository,
)
from .mocks import FakeHashingGateway


@pytest.fixture
def user_repository():
    return InMemoryUserRepository()


@pytest.fixture
def hash_gateway():
    return FakeHashingGateway()
