import pytest
from authentication_context.application.commands import AuthenticateWithSSOCommand
from authentication_context.application.use_cases import AuthenticateWithSSOUseCase
from authentication_context.domain.exceptions import InvalidSSOTokenException
from tests.authentication_context.unit.mocks import (
    FakeSSOTokenValidationGateway,
    FakeJWTTokenGateway,
)


@pytest.fixture
def use_case(sso_token_validation_gateway, jwt_token_gateway):
    return AuthenticateWithSSOUseCase(sso_token_validation_gateway, jwt_token_gateway)


@pytest.mark.asyncio
async def test_should_authenticate_valid_sso_token(
    use_case: AuthenticateWithSSOUseCase,
    sso_token_validation_gateway: FakeSSOTokenValidationGateway,
    jwt_token_gateway: FakeJWTTokenGateway,
):
    token = "valid_fake_token_123"
    provider = "fake"
    expected_user_id = "fake_user_456"
    expected_email = "user@company.com"
    expected_name = "John Doe"
    expected_claims = {"roles": ["user"], "tenant": "company"}

    sso_token_validation_gateway.set_valid_token(
        token=token,
        provider=provider,
        external_user_id=expected_user_id,
        email=expected_email,
        display_name=expected_name,
        claims=expected_claims,
    )

    command = AuthenticateWithSSOCommand(token=token, provider=provider)

    response = await use_case.execute(command)

    assert response.jwt_token == f"jwt_token_for_{expected_user_id}"
    assert response.external_user_id == expected_user_id
    assert response.email == expected_email
    assert response.display_name == expected_name
    assert response.provider == provider
    assert response.claims == expected_claims
    assert (token, provider) in sso_token_validation_gateway.validation_calls
    assert (expected_user_id, expected_claims) in jwt_token_gateway.generation_calls


@pytest.mark.asyncio
async def test_should_raise_exception_for_invalid_token(
    use_case: AuthenticateWithSSOUseCase,
    sso_token_validation_gateway: FakeSSOTokenValidationGateway,
):
    invalid_token = "invalid_token_123"
    provider = "fake"
    command = AuthenticateWithSSOCommand(token=invalid_token, provider=provider)

    with pytest.raises(InvalidSSOTokenException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_handle_different_sso_providers(
    use_case: AuthenticateWithSSOUseCase,
    sso_token_validation_gateway: FakeSSOTokenValidationGateway,
    jwt_token_gateway: FakeJWTTokenGateway,
):
    other_token = "token_456"
    other_provider = "other"
    other_user_id = "other_user_789"
    other_email = "user@gmail.com"
    other_name = "Jane Smith"
    other_claims = {}

    sso_token_validation_gateway.set_valid_token(
        token=other_token,
        provider=other_provider,
        external_user_id=other_user_id,
        email=other_email,
        display_name=other_name,
    )

    command = AuthenticateWithSSOCommand(token=other_token, provider=other_provider)

    response = await use_case.execute(command)

    assert response.jwt_token == f"jwt_token_for_{other_user_id}"
    assert response.external_user_id == other_user_id
    assert response.email == other_email
    assert response.display_name == other_name
    assert response.provider == other_provider
    assert (
        other_token,
        other_provider,
    ) in sso_token_validation_gateway.validation_calls
    assert (other_user_id, other_claims) in jwt_token_gateway.generation_calls
