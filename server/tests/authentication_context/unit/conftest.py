import pytest
from tests.authentication_context.unit.mocks import (
    FakeSSOProviderGateway,
    FakeJWTTokenGateway,
    FakeStateGenerationGateway,
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
