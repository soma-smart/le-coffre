import pytest
from uuid import UUID

from authentication_context.application.use_cases import AdminLoginUseCase
from authentication_context.application.commands import AdminLoginCommand
from authentication_context.domain.entities import AdminAccount, AuthenticationSession
from authentication_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)


@pytest.fixture
def use_case(
    admin_repository, password_hashing_gateway, jwt_token_gateway, session_repository
):
    return AdminLoginUseCase(
        admin_repository,
        password_hashing_gateway,
        jwt_token_gateway,
        session_repository,
    )


@pytest.mark.asyncio
async def test_should_authenticate_admin_and_return_jwt_token(
    use_case: AdminLoginUseCase, admin_repository, session_repository, jwt_token_gateway
):
    admin_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = "hashed(secure123!)"

    admin = AdminAccount(
        id=admin_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    admin_repository.save(admin)

    jwt_token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    assert response.jwt_token == "jwt_token_for_admin@lecoffre.com_uniqueness"
    assert response.admin_id == admin_id
    assert response.email == email

    # Check that session was created with the JWT token
    sessions = session_repository.get_sessions_by_user_id_ordered_by_creation(admin_id)
    assert len(sessions) == 1
    assert sessions[0].user_id == admin_id
    assert sessions[0].jwt_token == response.jwt_token


@pytest.mark.asyncio
async def test_should_raise_exception_for_wrong_password(
    use_case: AdminLoginUseCase, admin_repository, session_repository
):
    admin_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = "hashed(secure123!)"

    admin = AdminAccount(
        id=admin_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    admin_repository.save(admin)

    command = AdminLoginCommand(email=email, password="wrong_password")

    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(command)

    # No session should be created
    sessions = session_repository.get_sessions_by_user_id_ordered_by_creation(admin_id)
    assert len(sessions) == 0


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
    use_case: AdminLoginUseCase, admin_repository, jwt_token_gateway, session_repository
):
    admin_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = "hashed(secure123!)"
    old_jwt_token = "jwt_token_for_admin@lecoffre.com_uniqueness"

    admin = AdminAccount(
        id=admin_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    admin_repository.save(admin)

    session_repository.save(
        AuthenticationSession(
            user_id=admin_id,
            jwt_token=old_jwt_token,
        )
    )

    jwt_token_gateway.set_unique_jwt_part("other_uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    admin_session = session_repository.get_sessions_by_user_id_ordered_by_creation(
        admin_id
    )
    assert response.jwt_token == "jwt_token_for_admin@lecoffre.com_other_uniqueness"
    assert admin_session[-1].jwt_token == response.jwt_token
    assert admin_session[0].jwt_token == old_jwt_token
