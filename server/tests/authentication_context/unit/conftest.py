import pytest
from tests.authentication_context.unit.mocks import (
    FakeSSOProviderGateway,
    FakeJWTTokenGateway,
    FakeStateGenerationGateway,
    FakeAdminRepository,
    FakePasswordHashingGateway,
    FakeSessionRepository,
)


@pytest.fixture
def jwt_token_gateway():
    return FakeJWTTokenGateway()


@pytest.fixture
def sso_provider_gateway():
    return FakeSSOProviderGateway()


@pytest.fixture
def state_generation_gateway():
    return FakeStateGenerationGateway()


@pytest.fixture
def admin_repository():
    return FakeAdminRepository()


@pytest.fixture
def password_hashing_gateway():
    return FakePasswordHashingGateway()


@pytest.fixture
def session_repository():
    return FakeSessionRepository()
