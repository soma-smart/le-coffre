import pytest
from uuid import UUID
from datetime import datetime

from identity_access_management_context.application.use_cases.sso.sso_login_use_case import (
    SsoLoginUseCase,
)
from identity_access_management_context.application.use_cases import CreateUserUseCase
from identity_access_management_context.application.commands.sso_login_command import (
    SsoLoginCommand,
)
from identity_access_management_context.domain.exceptions import InvalidSsoCodeException
from tests.identity_access_management_context.unit.conftest import (
    create_sso_user_from_provider,
    create_existing_sso_user,
)


@pytest.fixture
def create_user_usecase(user_repository, password_hashing_gateway):
    return CreateUserUseCase(user_repository, password_hashing_gateway)


@pytest.fixture
def use_case(
    sso_gateway,
    sso_user_repository,
    create_user_usecase,
    token_gateway,
    time_provider,
):
    return SsoLoginUseCase(
        sso_gateway=sso_gateway,
        sso_user_repository=sso_user_repository,
        create_user_usecase=create_user_usecase,
        token_gateway=token_gateway,
        time_provider=time_provider,
    )


@pytest.mark.asyncio
async def test_should_authenticate_existing_sso_user_and_return_jwt_token(
    use_case: SsoLoginUseCase,
    sso_gateway,
    sso_user_repository,
    token_gateway,
):
    # Arrange
    sso_code = "valid_sso_code_123"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    display_name = "John Doe"
    sso_provider = "google"
    sso_user_id = "google_123456"

    sso_user_from_provider = create_sso_user_from_provider(
        email, display_name, sso_user_id, sso_provider
    )
    existing_sso_user = create_existing_sso_user(
        user_id, email, display_name, sso_user_id, sso_provider
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
async def test_should_raise_exception_for_invalid_sso_code(use_case: SsoLoginUseCase):
    # Arrange
    invalid_code = "invalid_sso_code_999"
    command = SsoLoginCommand(code=invalid_code)

    # Act & Assert
    with pytest.raises(InvalidSsoCodeException) as exc_info:
        await use_case.execute(command)

    assert "Invalid SSO code" in str(exc_info.value)


@pytest.mark.asyncio
async def test_should_create_new_user_for_first_time_sso_login(
    use_case: SsoLoginUseCase,
    sso_gateway,
    sso_user_repository,
    user_repository,
    token_gateway,
):
    # Arrange
    sso_code = "valid_new_user_code_456"
    email = "newuser@example.com"
    display_name = "Jane Smith"
    sso_provider = "azure"
    sso_user_id = "azure_789012"

    sso_user_from_provider = create_sso_user_from_provider(
        email, display_name, sso_user_id, sso_provider
    )

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
    sso_gateway,
    sso_user_repository,
    user_repository,
    token_gateway,
):
    # Arrange
    sso_code = "existing_user_code_789"
    user_id = UUID("9a852f2e-cc76-4928-93ef-9d546d7c77e6")
    email = "existinguser@example.com"
    display_name = "Existing User"
    sso_provider = "okta"
    sso_user_id = "okta_345678"
    old_login_time = datetime(2024, 1, 1, 12, 0, 0)

    existing_sso_user = create_existing_sso_user(
        user_id,
        email,
        display_name,
        sso_user_id,
        sso_provider,
        last_login=old_login_time,
    )
    sso_user_from_provider = create_sso_user_from_provider(
        email, display_name, sso_user_id, sso_provider
    )

    sso_user_repository.create(existing_sso_user)
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
    sso_gateway,
    sso_user_repository,
    token_gateway,
):
    sso_code = "valid_sso_code_123"
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    display_name = "John Doe"
    sso_provider = "google"
    sso_user_id = "google_123456"

    sso_user_from_provider = create_sso_user_from_provider(
        email, display_name, sso_user_id, sso_provider
    )
    existing_sso_user = create_existing_sso_user(
        user_id, email, display_name, sso_user_id, sso_provider
    )

    sso_gateway.set_valid_code(sso_code, sso_user_from_provider)
    sso_user_repository.create(existing_sso_user)
    token_gateway.set_unique_jwt_part("unique_token_part")

    command = SsoLoginCommand(code=sso_code)

    response = await use_case.execute(command)

    assert response.refresh_token == f"refresh_token_for_{user_id}_unique_token_part"
    assert response.refresh_token != response.jwt_token
