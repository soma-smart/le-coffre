import pytest
from authentication_context.application.use_cases import (
    InitiateSSOLoginUseCase,
)
from tests.authentication_context.unit.mocks import (
    FakeSSOProviderGateway,
    FakeStateGenerationGateway,
)


@pytest.fixture
def use_case(sso_provider_gateway, state_generation_gateway):
    return InitiateSSOLoginUseCase(sso_provider_gateway, state_generation_gateway)


@pytest.mark.asyncio
async def test_should_initiate_sso_login_and_return_authorization_url(
    use_case: InitiateSSOLoginUseCase,
    sso_provider_gateway: FakeSSOProviderGateway,
    state_generation_gateway: FakeStateGenerationGateway,
):
    state = "random_state_123"
    provider_name = "fake"
    sso_provider_gateway.set_provider_name(provider_name)
    state_generation_gateway.set_state(state)

    response = await use_case.execute()

    expected_url = f"https://{provider_name}.com/oauth/authorize?state={state}&client_id=fake_client&redirect_uri=http://localhost/callback"
    assert response.authorization_url == expected_url
    assert response.state == state
    assert state in sso_provider_gateway.authorization_calls
    assert state in state_generation_gateway.generation_calls
