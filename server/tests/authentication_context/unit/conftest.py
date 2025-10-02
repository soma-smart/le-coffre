import pytest
from tests.authentication_context.unit.mocks import (
    FakeTokenGateway,
    FakeStateGenerationGateway,
    FakePasswordHashingGateway,
    FakeSessionRepository,
    FakeUserPasswordRepository,
    FakeUserManagementGateway,
    FakeSsoGateway,
    FakeSsoUserRepository,
)


@pytest.fixture
def token_gateway():
    return FakeTokenGateway()


@pytest.fixture
def state_generation_gateway():
    return FakeStateGenerationGateway()


@pytest.fixture
def password_hashing_gateway():
    return FakePasswordHashingGateway()


@pytest.fixture
def session_repository():
    return FakeSessionRepository()


@pytest.fixture
def user_password_repository():
    return FakeUserPasswordRepository()


@pytest.fixture
def user_management_gateway():
    return FakeUserManagementGateway()


@pytest.fixture
def sso_gateway():
    return FakeSsoGateway()


@pytest.fixture
def sso_user_repository():
    return FakeSsoUserRepository()
