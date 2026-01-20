import pytest
from sqlmodel import Session, create_engine, select
from identity_access_management_context.adapters.secondary.sql.model.sso_configuration_model import (
    SsoConfigurationTable,
    create_sso_configuration_table,
)
from identity_access_management_context.adapters.secondary.sql.sql_sso_gateway import (
    SqlSsoGateway,
)
from identity_access_management_context.domain.exceptions import (
    InvalidSsoCodeException,
    InvalidSsoSettingsException,
)


@pytest.fixture
def db_engine():
    """Create a temporary in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    create_sso_configuration_table(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create a new database session for each test."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def sso_gateway(db_session):
    """Create SqlSsoGateway instance with test session."""
    return SqlSsoGateway(db_session)


# TDD Cycle 1: configure_with_discovery - no existing configuration
@pytest.mark.asyncio
async def test_configure_with_discovery_creates_new_configuration(
    sso_gateway, db_session, oidc_server
):
    """Given no configuration exists, When configuring with valid discovery URL, Then configuration is stored."""
    # Arrange
    client_id = oidc_server["client_id"]
    client_secret = oidc_server["client_secret"]
    discovery_url = oidc_server["discovery_url"]

    # Act
    await sso_gateway.configure_with_discovery(client_id, client_secret, discovery_url)

    # Assert
    statement = select(SsoConfigurationTable).where(SsoConfigurationTable.id == 1)
    stored_config = db_session.exec(statement).first()
    assert stored_config is not None
    assert stored_config.client_id == client_id
    assert stored_config.client_secret == client_secret
    assert stored_config.discovery_url == discovery_url
    assert stored_config.authorization_endpoint is not None
    assert stored_config.token_endpoint is not None
    assert stored_config.userinfo_endpoint is not None


# TDD Cycle 2: configure_with_discovery - upsert existing configuration
@pytest.mark.asyncio
async def test_configure_with_discovery_updates_existing_configuration(
    sso_gateway, db_session, oidc_server
):
    """Given existing configuration, When configuring again, Then configuration is updated (upsert)."""
    # Arrange - Create initial configuration
    initial_client_id = "initial-client-id"
    initial_client_secret = "initial-client-secret"
    await sso_gateway.configure_with_discovery(
        initial_client_id, initial_client_secret, oidc_server["discovery_url"]
    )

    # Act - Update with new credentials
    new_client_id = oidc_server["client_id"]
    new_client_secret = oidc_server["client_secret"]
    await sso_gateway.configure_with_discovery(
        new_client_id, new_client_secret, oidc_server["discovery_url"]
    )

    # Assert - Should have only one row with updated values
    statement = select(SsoConfigurationTable)
    all_configs = db_session.exec(statement).all()
    assert len(all_configs) == 1, "Should only have one configuration row"

    stored_config = all_configs[0]
    assert stored_config.id == 1
    assert stored_config.client_id == new_client_id
    assert stored_config.client_secret == new_client_secret
    assert stored_config.discovery_url == oidc_server["discovery_url"]


# TDD Cycle 3: configure_with_discovery - invalid discovery URL
@pytest.mark.asyncio
async def test_configure_with_discovery_invalid_url_raises_exception(sso_gateway):
    """Given invalid discovery URL, When configuring, Then raises InvalidSsoSettingsException."""
    # Arrange
    client_id = "test-client-id"
    client_secret = "test-client-secret"
    invalid_discovery_url = "https://invalid-server-that-does-not-exist.com/.well-known/openid-configuration"

    # Act & Assert
    with pytest.raises(InvalidSsoSettingsException):
        await sso_gateway.configure_with_discovery(
            client_id, client_secret, invalid_discovery_url
        )


# TDD Cycle 4: get_authorize_url - configured gateway
@pytest.mark.asyncio
async def test_get_authorize_url_returns_valid_url(sso_gateway, oidc_server):
    """Given configured gateway, When getting authorize URL, Then returns valid OAuth URL."""
    # Arrange
    await sso_gateway.configure_with_discovery(
        oidc_server["client_id"],
        oidc_server["client_secret"],
        oidc_server["discovery_url"],
    )

    # Act
    authorize_url = await sso_gateway.get_authorize_url()

    # Assert
    assert authorize_url is not None
    assert oidc_server["issuer_url"] in authorize_url
    assert "response_type=code" in authorize_url
    assert f"client_id={oidc_server['client_id']}" in authorize_url


# TDD Cycle 5: get_authorize_url - unconfigured gateway
@pytest.mark.asyncio
async def test_get_authorize_url_unconfigured_raises_exception(sso_gateway):
    """Given unconfigured gateway, When getting authorize URL, Then raises exception."""
    # Act & Assert
    with pytest.raises(InvalidSsoSettingsException):
        await sso_gateway.get_authorize_url()


# TDD Cycle 6: validate_callback - valid OAuth code
@pytest.mark.asyncio
async def test_validate_callback_with_valid_code_returns_user_info(
    sso_gateway, oidc_server, oidc_test_user
):
    """Given valid OAuth code, When validating callback, Then returns SsoUserInfo."""
    # Arrange
    await sso_gateway.configure_with_discovery(
        oidc_server["client_id"],
        oidc_server["client_secret"],
        oidc_server["discovery_url"],
    )

    # Get authorization URL
    auth_url = await sso_gateway.get_authorize_url()

    # Simulate user authorization by posting to the mock provider
    import httpx
    from urllib.parse import urlparse, parse_qs

    response = httpx.post(
        auth_url,
        data={"sub": oidc_test_user["sub"]},
        follow_redirects=False,
    )

    # Extract authorization code from callback URL
    callback_url = response.headers.get("location", "")
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    code = query_params.get("code", [None])[0]

    assert code, "Should have received an authorization code"

    # Act
    user_info = await sso_gateway.validate_callback(code)

    # Assert
    assert user_info is not None
    assert user_info.email == oidc_test_user["email"]
    assert user_info.display_name == oidc_test_user["name"]
    assert user_info.sso_user_id == oidc_test_user["sub"]


# TDD Cycle 7: validate_callback - invalid code
@pytest.mark.asyncio
async def test_validate_callback_with_invalid_code_raises_exception(
    sso_gateway, oidc_server
):
    """Given invalid OAuth code, When validating callback, Then raises InvalidSsoCodeException."""
    # Arrange
    await sso_gateway.configure_with_discovery(
        oidc_server["client_id"],
        oidc_server["client_secret"],
        oidc_server["discovery_url"],
    )

    # Act & Assert
    with pytest.raises(InvalidSsoCodeException):
        await sso_gateway.validate_callback("invalid-code-12345")


# TDD Cycle 8: validate_callback - unconfigured gateway
@pytest.mark.asyncio
async def test_validate_callback_unconfigured_raises_exception(sso_gateway):
    """Given unconfigured gateway, When validating callback, Then raises exception."""
    # Act & Assert
    with pytest.raises(InvalidSsoSettingsException):
        await sso_gateway.validate_callback("any-code")
