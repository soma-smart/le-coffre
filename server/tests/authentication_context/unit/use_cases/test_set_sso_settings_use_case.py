import pytest
from authentication_context.application.use_cases import (
    SsoSetSettingsUseCase,
)


@pytest.fixture
def use_case(sso_gateway):
    return SsoSetSettingsUseCase(sso_gateway)


def test_set_client_settings_use_case(use_case, sso_gateway):
    # Given
    client_id = "test_client_id"
    client_secret = "test_client_secret"

    # When
    use_case.execute(
        client_id=client_id,
        client_secret=client_secret,
    )
    # Then
    assert sso_gateway._client_id == client_id
    assert sso_gateway._client_secret == client_secret
