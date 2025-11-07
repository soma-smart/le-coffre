import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import AdminLoginUseCase
from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.domain.entities import (
    UserPassword,
)
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)


@pytest.fixture
def use_case(
    user_password_repository,
    password_hashing_gateway,
    token_gateway,
):
    return AdminLoginUseCase(
        user_password_repository,
        password_hashing_gateway,
        token_gateway,
    )


@pytest.mark.asyncio
async def test_should_authenticate_admin_and_return_jwt_token(
    use_case: AdminLoginUseCase,
    user_password_repository,
    token_gateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = "hashed(secure123!)"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    user_password_repository.save(user_password)

    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    assert response.jwt_token == f"jwt_token_for_{user_id}_uniqueness"
    assert response.admin_id == user_id
    assert response.email == email


@pytest.mark.asyncio
async def test_should_raise_exception_for_wrong_password(
    use_case: AdminLoginUseCase, user_password_repository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = "hashed(secure123!)"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")

    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_raise_exception_for_non_existent_admin(
    use_case: AdminLoginUseCase,
):
    command = AdminLoginCommand(
        email="nonexistent@lecoffre.com", password="any_password"
    )

    with pytest.raises(AdminNotFoundException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_return_refresh_token_on_successful_login(
    use_case: AdminLoginUseCase,
    user_password_repository,
    token_gateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = "hashed(secure123!)"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    user_password_repository.save(user_password)

    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    assert response.refresh_token == f"refresh_token_for_{user_id}_uniqueness"
    assert response.refresh_token != response.jwt_token
