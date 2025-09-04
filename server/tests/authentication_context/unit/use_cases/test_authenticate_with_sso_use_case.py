import pytest
from authentication_context.application.commands import AuthenticateWithSSOCommand
from authentication_context.application.use_cases import AuthenticateWithSSOUseCase
from authentication_context.domain.exceptions import InvalidSSOTokenException
from tests.authentication_context.unit.mocks import (
    FakeSSOProviderGateway,
    FakeJWTTokenGateway,
)


@pytest.fixture
def use_case(sso_provider_gateway, jwt_token_gateway):
    return AuthenticateWithSSOUseCase(sso_provider_gateway, jwt_token_gateway)


@pytest.mark.asyncio
async def test_should_authenticate_valid_sso_token(
    use_case: AuthenticateWithSSOUseCase,
    sso_provider_gateway: FakeSSOProviderGateway,
    jwt_token_gateway: FakeJWTTokenGateway,
):
    token = "valid_fake_token_123"
    expected_user_id = "fake_user_456"
    expected_email = "user@company.com"
    expected_name = "John Doe"
    expected_claims = {"roles": ["user"], "tenant": "company"}
    provider_name = "fake"

    sso_provider_gateway.set_provider_name(provider_name)
    sso_provider_gateway.set_valid_token(
        token=token,
        external_user_id=expected_user_id,
        email=expected_email,
        display_name=expected_name,
        claims=expected_claims,
    )

    jwt_token_gateway.set_unique_jwt_part("uniqueness")

    command = AuthenticateWithSSOCommand(token=token)

    response = await use_case.execute(command)

    assert response.jwt_token == f"jwt_token_for_{expected_user_id}_uniqueness"
    assert response.external_user_id == expected_user_id
    assert response.email == expected_email
    assert response.display_name == expected_name
    assert response.provider == provider_name
    assert response.claims == expected_claims
    assert token in sso_provider_gateway.validation_calls
    assert (expected_user_id, expected_claims) in jwt_token_gateway.generation_calls


@pytest.mark.asyncio
async def test_should_raise_exception_for_invalid_token(
    use_case: AuthenticateWithSSOUseCase,
    sso_provider_gateway: FakeSSOProviderGateway,
):
    sso_provider_gateway.set_provider_name("fake")
    invalid_token = "invalid_token_123"
    command = AuthenticateWithSSOCommand(token=invalid_token)

    with pytest.raises(InvalidSSOTokenException):
        await use_case.execute(command)
