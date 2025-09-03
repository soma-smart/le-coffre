import pytest
from tests.authentication_context.unit.mocks import (
    FakeSSOTokenValidationGateway,
    FakeJWTTokenGateway,
)


@pytest.fixture
def sso_token_validation_gateway():
    return FakeSSOTokenValidationGateway()


@pytest.fixture
def jwt_token_gateway():
    return FakeJWTTokenGateway()
