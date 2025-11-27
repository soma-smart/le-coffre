import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import (
    RegisterWithPasswordUseCase,
)
from identity_access_management_context.application.commands import (
    RegisterWithPasswordCommand,
)
from identity_access_management_context.domain.exceptions import (
    UserAlreadyExistsException,
)


@pytest.fixture
def use_case(
    user_password_repository, password_hashing_gateway, user_management_gateway
):
    return RegisterWithPasswordUseCase(
        user_password_repository, password_hashing_gateway, user_management_gateway
    )


@pytest.mark.asyncio
async def test_should_register_first_user_as_admin_with_password_and_return_user_id(
    use_case: RegisterWithPasswordUseCase,
    user_password_repository,
    user_management_gateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password = "secure123!"
    display_name = "Admin User"

    command = RegisterWithPasswordCommand(
        id=user_id, email=email, password=password, display_name=display_name
    )

    result = await use_case.execute(command)

    assert result == user_id

    saved_user_password = user_password_repository.get_by_id(user_id)
    assert saved_user_password.id == user_id
    assert saved_user_password.email == email
    assert saved_user_password.display_name == display_name
    assert saved_user_password.password_hash == "hashed(secure123!)"


@pytest.mark.asyncio
async def test_should_raise_exception_when_email_already_exists(
    use_case: RegisterWithPasswordUseCase, user_password_repository
):
    # Pre-register a user with the same email
    existing_user_id = UUID("00000000-0000-0000-0000-000000000001")
    existing_email = "admin@lecoffre.com"
    from identity_access_management_context.domain.entities import UserPassword

    existing_user = UserPassword(
        id=existing_user_id,
        email=existing_email,
        password_hash="existing_hash",
        display_name="Existing Admin",
    )
    user_password_repository.save(existing_user)

    # Try to register another user with the same email
    new_user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    command = RegisterWithPasswordCommand(
        id=new_user_id,
        email=existing_email,
        password="secure123!",
        display_name="New User",
    )

    with pytest.raises(UserAlreadyExistsException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_hash_password_before_storing_credentials(
    use_case: RegisterWithPasswordUseCase, user_password_repository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    plain_password = "my_plain_password"
    display_name = "Admin User"

    command = RegisterWithPasswordCommand(
        id=user_id, email=email, password=plain_password, display_name=display_name
    )

    await use_case.execute(command)

    saved_user_password = user_password_repository.get_by_id(user_id)
    assert saved_user_password.password_hash == "hashed(my_plain_password)"
    assert saved_user_password.password_hash != plain_password


@pytest.mark.asyncio
async def test_should_delegate_admin_creation_to_user_management_context_for_first_user(
    use_case: RegisterWithPasswordUseCase, user_management_gateway
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"

    command = RegisterWithPasswordCommand(
        id=user_id, email=email, password="password123", display_name=display_name
    )

    await use_case.execute(command)

    created_admins = user_management_gateway.get_created_admins()
    assert len(created_admins) == 1
    assert created_admins[0]["user_id"] == user_id
    assert created_admins[0]["email"] == email
    assert created_admins[0]["display_name"] == display_name


@pytest.mark.asyncio
async def test_should_create_regular_user_for_second_registration(
    use_case: RegisterWithPasswordUseCase, user_management_gateway
):
    # First user - should become admin
    first_user_id = UUID("00000000-0000-0000-0000-000000000001")
    first_command = RegisterWithPasswordCommand(
        id=first_user_id,
        email="first@lecoffre.com",
        password="password123",
        display_name="First User",
    )
    await use_case.execute(first_command)

    # Second user - should become regular user
    second_user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    second_command = RegisterWithPasswordCommand(
        id=second_user_id,
        email="second@lecoffre.com",
        password="password456",
        display_name="Second User",
    )
    await use_case.execute(second_command)

    # Verify first user is admin
    created_admins = user_management_gateway.get_created_admins()
    assert len(created_admins) == 1
    assert created_admins[0]["user_id"] == first_user_id

    # Verify second user is regular user
    created_users = user_management_gateway.get_created_users()
    assert len(created_users) == 1
    assert created_users[0]["user_id"] == second_user_id
    assert created_users[0]["email"] == "second@lecoffre.com"
    assert created_users[0]["display_name"] == "Second User"
