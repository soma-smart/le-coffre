from datetime import datetime
from uuid import UUID

import pytest

from identity_access_management_context.application.commands import (
    SsoLoginCommand,
)
from identity_access_management_context.application.use_cases import (
    SsoLoginUseCase,
)
from identity_access_management_context.domain.entities import SsoConfiguration, User
from identity_access_management_context.domain.events import SsoLoginEvent
from identity_access_management_context.domain.exceptions import InvalidSsoCodeException
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from tests.identity_access_management_context.unit.conftest import (
    create_existing_sso_user,
    create_sso_user_from_provider,
)

from ..fakes import (
    FakeGroupMemberRepository,
    FakeGroupRepository,
    FakePasswordHashingGateway,
    FakeSsoConfigurationRepository,
    FakeSsoEncryptionGateway,
    FakeSsoGateway,
    FakeSsoUserRepository,
    FakeTimeGateway,
    FakeTokenGateway,
    FakeUserRepository,
)


@pytest.fixture
def use_case(
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    token_gateway: FakeTokenGateway,
    time_provider: FakeTimeGateway,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    sso_encryption_gateway: FakeSsoEncryptionGateway,
    event_publisher,
    sso_event_repository,
):
    return SsoLoginUseCase(
        sso_gateway=sso_gateway,
        sso_user_repository=sso_user_repository,
        user_repository=user_repository,
        password_hashing_gateway=password_hashing_gateway,
        token_gateway=token_gateway,
        time_provider=time_provider,
        group_repository=group_repository,
        group_member_repository=group_member_repository,
        sso_configuration_repository=sso_configuration_repository,
        sso_encryption_gateway=sso_encryption_gateway,
        event_publisher=event_publisher,
        sso_event_repository=sso_event_repository,
    )


@pytest.mark.asyncio
async def test_should_authenticate_existing_sso_user_and_return_jwt_token(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    token_gateway: FakeTokenGateway,
):
    # Arrange
    sso_code = "valid_sso_code_123"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    display_name = "John Doe"
    sso_provider = "google"
    sso_user_id = "google_123456"

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)
    existing_sso_user = create_existing_sso_user(user_id, email, display_name, sso_user_id, sso_provider)
    user_repository.save(
        User(
            id=user_id,
            username="johndoe",
            email=email,
            name=display_name,
            roles=[],
        )
    )

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )
    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    sso_user_repository.create(existing_sso_user)
    token_gateway.set_unique_jwt_part("unique_token_part")

    command = SsoLoginCommand(code=sso_code)

    # Act
    response = await use_case.execute(command)

    # Assert
    assert response.jwt_token == f"jwt_token_for_{user_id}_unique_token_part"
    assert response.user_id == user_id
    assert response.email == email
    assert response.display_name == display_name
    assert response.is_new_user is False


@pytest.mark.asyncio
async def test_should_raise_exception_for_invalid_sso_code(
    use_case: SsoLoginUseCase,
    sso_configuration_repository: FakeSsoConfigurationRepository,
):
    # Arrange
    invalid_code = "invalid_sso_code_999"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )
    command = SsoLoginCommand(code=invalid_code)

    # Act & Assert
    with pytest.raises(InvalidSsoCodeException) as exc_info:
        await use_case.execute(command)

    assert "Invalid SSO code" in str(exc_info.value)


@pytest.mark.asyncio
async def test_should_create_new_user_for_first_time_sso_login(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    sso_configuration_repository: FakeSsoConfigurationRepository,
):
    # Arrange
    sso_code = "valid_new_user_code_456"
    email = "newuser@example.com"
    display_name = "Jane Smith"
    sso_provider = "azure"
    sso_user_id = "azure_789012"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)

    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    assert sso_user_repository.get_by_sso_user_id(sso_user_id, sso_provider) is None
    token_gateway.set_unique_jwt_part("new_user_token")

    command = SsoLoginCommand(code=sso_code)

    # Act
    response = await use_case.execute(command)

    # Assert
    # Check that user was created in User repository
    created_user = user_repository.get_by_id(response.user_id)
    assert created_user is not None
    assert created_user.email == email
    assert created_user.name == display_name
    assert created_user.id == response.user_id


@pytest.mark.asyncio
async def test_should_update_last_login_for_existing_user_without_recreation(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    token_gateway: FakeTokenGateway,
):
    # Arrange
    sso_code = "existing_user_code_789"
    user_id = UUID("9a852f2e-cc76-4928-93ef-9d546d7c77e6")
    email = "existinguser@example.com"
    display_name = "Existing User"
    sso_provider = "okta"
    sso_user_id = "okta_345678"
    old_login_time = datetime(2024, 1, 1, 12, 0, 0)

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    existing_sso_user = create_existing_sso_user(
        user_id,
        email,
        display_name,
        sso_user_id,
        sso_provider,
        last_login=old_login_time,
    )
    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)

    sso_user_repository.create(existing_sso_user)
    user_repository.save(
        User(
            id=user_id,
            username="existinguser",
            email=email,
            name=display_name,
            roles=[],
        )
    )
    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    token_gateway.set_unique_jwt_part("existing_user_token")

    # Count initial users
    initial_users = user_repository.list_all()
    initial_user_count = len(initial_users)

    command = SsoLoginCommand(code=sso_code)

    # Act
    await use_case.execute(command)

    # Assert
    # Check that NO new user was created
    current_users = user_repository.list_all()
    assert len(current_users) == initial_user_count

    # Check that last_login was updated
    updated_sso_user = sso_user_repository.get_by_sso_user_id(sso_user_id, sso_provider)
    assert updated_sso_user.last_login > old_login_time


@pytest.mark.asyncio
async def test_should_return_refresh_token_on_successful_sso_login(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    token_gateway: FakeTokenGateway,
):
    sso_code = "valid_sso_code_123"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    display_name = "John Doe"
    sso_provider = "google"
    sso_user_id = "google_123456"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)
    existing_sso_user = create_existing_sso_user(user_id, email, display_name, sso_user_id, sso_provider)

    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    sso_user_repository.create(existing_sso_user)
    user_repository.save(User(id=user_id, username="johndoe", email=email, name=display_name, roles=[]))
    token_gateway.set_unique_jwt_part("unique_token_part")

    command = SsoLoginCommand(code=sso_code)

    response = await use_case.execute(command)

    assert response.refresh_token == f"refresh_token_for_{user_id}_unique_token_part"
    assert response.refresh_token != response.jwt_token


@pytest.mark.asyncio
async def test_when_no_sso_config_when_login_should_fail(use_case: SsoLoginUseCase):
    with pytest.raises(ValueError):
        await use_case.execute(SsoLoginCommand(code="invalid_code"))


@pytest.mark.asyncio
async def test_should_publish_sso_login_event_on_successful_login(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    token_gateway: FakeTokenGateway,
    event_publisher: FakeDomainEventPublisher,
):
    sso_code = "valid_sso_code_123"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    display_name = "John Doe"
    sso_provider = "google"
    sso_user_id = "google_123456"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)
    existing_sso_user = create_existing_sso_user(user_id, email, display_name, sso_user_id, sso_provider)

    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    sso_user_repository.create(existing_sso_user)
    user_repository.save(User(id=user_id, username="johndoe", email=email, name=display_name, roles=[]))
    token_gateway.set_unique_jwt_part("unique_token_part")

    command = SsoLoginCommand(code=sso_code)
    await use_case.execute(command)

    events = event_publisher.get_published_events_of_type(SsoLoginEvent)
    assert len(events) == 1
    assert events[0].user_id == user_id
    assert events[0].email == email
    assert events[0].is_new_user is False


@pytest.mark.asyncio
async def test_should_store_sso_login_event_on_successful_login(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    token_gateway: FakeTokenGateway,
    sso_event_repository,
):
    sso_code = "valid_sso_code_123"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    display_name = "John Doe"
    sso_provider = "google"
    sso_user_id = "google_123456"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)
    existing_sso_user = create_existing_sso_user(user_id, email, display_name, sso_user_id, sso_provider)

    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    sso_user_repository.create(existing_sso_user)
    user_repository.save(User(id=user_id, username="johndoe", email=email, name=display_name, roles=[]))
    token_gateway.set_unique_jwt_part("unique_token_part")

    command = SsoLoginCommand(code=sso_code)
    await use_case.execute(command)

    assert len(sso_event_repository.events) == 1
    stored = sso_event_repository.events[0]
    assert stored["event_type"] == "SsoLoginEvent"
    assert stored["actor_user_id"] == user_id


@pytest.mark.asyncio
async def test_should_raise_runtime_error_when_existing_sso_user_has_no_corresponding_user(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
):
    sso_code = "valid_code_orphan_sso"
    user_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    email = "orphan_sso@example.com"
    display_name = "Orphan SSO User"
    sso_provider = "google"
    sso_user_id = "google_orphan_123"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)
    existing_sso_user = create_existing_sso_user(user_id, email, display_name, sso_user_id, sso_provider)

    sso_user_repository.create(existing_sso_user)
    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    # Intentionally NOT seeding user_repository to trigger the RuntimeError

    with pytest.raises(RuntimeError, match="User should exist at this point"):
        await use_case.execute(SsoLoginCommand(code=sso_code))


@pytest.mark.asyncio
async def test_should_return_admin_role_in_token_when_sso_user_has_been_promoted(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    sso_configuration_repository: FakeSsoConfigurationRepository,
):
    # Given an existing SSO user who has been promoted to admin in the DB
    sso_code = "valid_sso_code_promoted"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "promoted_sso@example.com"
    display_name = "Promoted SSO User"
    sso_provider = "google"
    sso_user_id = "google_promoted_123"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)
    existing_sso_user = create_existing_sso_user(user_id, email, display_name, sso_user_id, sso_provider)

    sso_user_repository.create(existing_sso_user)
    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    token_gateway.set_unique_jwt_part("promoted_token_part")

    # User has been promoted to admin in the User repository
    promoted_user = User(
        id=user_id,
        username="promoted_sso",
        email=email,
        name=display_name,
        roles=["admin"],
    )
    user_repository.save(promoted_user)

    # When the SSO user logs in again (e.g. next day after token expiry)
    command = SsoLoginCommand(code=sso_code)
    await use_case.execute(command)

    # Then the generated token should reflect the current DB roles
    generated_token = token_gateway.get_last_generated_token()
    assert generated_token is not None
    assert generated_token.roles == ["admin"]


@pytest.mark.asyncio
async def test_should_propagate_redirect_uri_to_gateway_when_provided_in_command(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    token_gateway: FakeTokenGateway,
):
    # Arrange
    sso_code = "valid_sso_code_cli"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "cli_user@example.com"
    display_name = "CLI User"
    sso_provider = "azure"
    sso_user_id = "azure_cli_123"
    cli_redirect_uri = "http://localhost:9876/callback"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)
    existing_sso_user = create_existing_sso_user(user_id, email, display_name, sso_user_id, sso_provider)

    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    sso_user_repository.create(existing_sso_user)
    user_repository.save(User(id=user_id, username="cliuser", email=email, name=display_name, roles=[]))
    token_gateway.set_unique_jwt_part("cli_token_part")

    command = SsoLoginCommand(code=sso_code, redirect_uri=cli_redirect_uri)

    # Act
    await use_case.execute(command)

    # Assert: the gateway received the redirect_uri from the command
    assert sso_gateway.last_redirect_uri == cli_redirect_uri


@pytest.mark.asyncio
async def test_should_not_pass_redirect_uri_to_gateway_when_not_provided(
    use_case: SsoLoginUseCase,
    sso_gateway: FakeSsoGateway,
    sso_user_repository: FakeSsoUserRepository,
    user_repository: FakeUserRepository,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    token_gateway: FakeTokenGateway,
):
    # Arrange
    sso_code = "valid_sso_code_browser"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "browser_user@example.com"
    display_name = "Browser User"
    sso_provider = "azure"
    sso_user_id = "azure_browser_456"

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    sso_user_from_provider = create_sso_user_from_provider(email, display_name, sso_user_id, sso_provider)
    existing_sso_user = create_existing_sso_user(user_id, email, display_name, sso_user_id, sso_provider)

    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    sso_user_repository.create(existing_sso_user)
    user_repository.save(User(id=user_id, username="browseruser", email=email, name=display_name, roles=[]))
    token_gateway.set_unique_jwt_part("browser_token_part")

    command = SsoLoginCommand(code=sso_code)

    # Act
    await use_case.execute(command)

    # Assert: the gateway received None (no redirect_uri override)
    assert sso_gateway.last_redirect_uri is None
