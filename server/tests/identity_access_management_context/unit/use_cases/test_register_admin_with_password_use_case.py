import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import (
    RegisterAdminWithPasswordUseCase,
)
from identity_access_management_context.application.commands import (
    RegisterAdminWithPasswordCommand,
)
from identity_access_management_context.domain.exceptions import (
    AdminAlreadyExistsException,
)


@pytest.fixture
def use_case(
    user_password_repository,
    password_hashing_gateway,
    user_management_gateway,
):
    return RegisterAdminWithPasswordUseCase(
        user_password_repository,
        password_hashing_gateway,
        user_management_gateway,
    )


@pytest.mark.asyncio
async def test_should_register_first_admin_with_password_and_return_user_id(
    use_case: RegisterAdminWithPasswordUseCase,
    user_password_repository,
    user_management_gateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password = "secure123!"
    display_name = "Admin User"

    command = RegisterAdminWithPasswordCommand(
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
async def test_should_raise_exception_when_admin_already_exists(
    use_case: RegisterAdminWithPasswordUseCase, user_management_gateway
):
    user_management_gateway.set_admin_exists(True)

    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    command = RegisterAdminWithPasswordCommand(
        id=user_id,
        email="new@lecoffre.com",
        password="secure123!",
        display_name="New Admin",
    )

    with pytest.raises(AdminAlreadyExistsException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_hash_password_before_storing_credentials(
    use_case: RegisterAdminWithPasswordUseCase, user_password_repository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    plain_password = "my_plain_password"
    display_name = "Admin User"

    command = RegisterAdminWithPasswordCommand(
        id=user_id, email=email, password=plain_password, display_name=display_name
    )

    await use_case.execute(command)

    saved_user_password = user_password_repository.get_by_id(user_id)
    assert saved_user_password.password_hash == "hashed(my_plain_password)"
    assert saved_user_password.password_hash != plain_password


@pytest.mark.asyncio
async def test_should_delegate_admin_creation_to_user_management_context(
    use_case: RegisterAdminWithPasswordUseCase, user_management_gateway
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"

    command = RegisterAdminWithPasswordCommand(
        id=user_id, email=email, password="password123", display_name=display_name
    )

    await use_case.execute(command)

    created_admins = user_management_gateway.get_created_admins()
    assert len(created_admins) == 1
    assert created_admins[0]["user_id"] == user_id
    assert created_admins[0]["email"] == email
    assert created_admins[0]["display_name"] == display_name
