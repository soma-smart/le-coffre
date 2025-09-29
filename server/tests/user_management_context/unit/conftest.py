import pytest

from user_management_context.adapters.output.interfaces import (
    InMemoryUserRepository,
)


@pytest.fixture
def user_repository():
    return InMemoryUserRepository()
