import pytest
from uuid import UUID

from authentication_context.application.use_cases import AdminLoginUseCase
from authentication_context.application.commands import AdminLoginCommand
from authentication_context.domain.entities import UserPassword, AuthenticationSession
from authentication_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)


@pytest.fixture
def use_case(
    user_password_repository,
    password_hashing_gateway,
    token_gateway,
    session_repository,
):
    return AdminLoginUseCase(
        user_password_repository,
        password_hashing_gateway,
        token_gateway,
        session_repository,
    )


@pytest.mark.asyncio
async def test_should_authenticate_admin_and_return_jwt_token(
    use_case: AdminLoginUseCase,
    user_password_repository,
    session_repository,
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

    # Check that session was created with the JWT token
    sessions = session_repository.get_user_last_session(user_id)
    assert sessions.user_id == user_id
    assert sessions.jwt_token == response.jwt_token


@pytest.mark.asyncio
async def test_should_raise_exception_for_wrong_password(
    use_case: AdminLoginUseCase, user_password_repository, session_repository
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

    # No session should be created
    assert session_repository.get_user_last_session(user_id) is None


@pytest.mark.asyncio
async def test_should_raise_exception_for_non_existent_admin(
    use_case: AdminLoginUseCase, session_repository
):
    command = AdminLoginCommand(
        email="nonexistent@lecoffre.com", password="any_password"
    )

    with pytest.raises(AdminNotFoundException):
        await use_case.execute(command)

    # No session should be created
    assert len(session_repository._sessions) == 0


@pytest.mark.asyncio
async def test_should_store_new_session_on_successful_login(
    use_case: AdminLoginUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = "hashed(secure123!)"
    old_jwt_token = f"jwt_token_for_{user_id}_uniqueness"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    user_password_repository.save(user_password)

    session_repository.save(
        AuthenticationSession(
            user_id=user_id,
            jwt_token=old_jwt_token,
        )
    )

    token_gateway.set_unique_jwt_part("other_uniqueness")

    old_session = session_repository.get_user_last_session(user_id)

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    admin_session = session_repository.get_user_last_session(user_id)
    assert response.jwt_token == f"jwt_token_for_{user_id}_other_uniqueness"
    assert admin_session.jwt_token == response.jwt_token
    assert admin_session.created_at > old_session.created_at
