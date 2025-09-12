import pytest

from user_management_context.adapters.output.interfaces import (
    InMemoryUserRepository,
)
from .mocks import FakeHashingGateway
from tests.mocks.fake_access_controller import (
    FakeAccessController,
)


@pytest.fixture
def user_repository():
    return InMemoryUserRepository()


@pytest.fixture
def hash_gateway():
    return FakeHashingGateway()


@pytest.fixture
def access_controller():
    return FakeAccessController()
