import pytest
from uuid import UUID

from authentication_context.application.use_cases import ValidateUserTokenUseCase
from authentication_context.application.commands import ValidateUserTokenCommand
from authentication_context.domain.entities import UserPassword, AuthenticationSession
from authentication_context.domain.exceptions import (
    InvalidTokenException,
    SessionNotFoundException,
    UserNotFoundException,
    InsufficientRoleException,
)


@pytest.fixture
def use_case(user_password_repository, token_gateway, session_repository):
    return ValidateUserTokenUseCase(
        user_password_repository, token_gateway, session_repository
    )


@pytest.mark.asyncio
async def test_should_validate_token_and_return_user_details(
    use_case: ValidateUserTokenUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"
    jwt_token = "jwt_token_for_admin@lecoffre.com_abc123"

    # Setup user password
    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash="hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    # Setup session
    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    # Setup JWT token validation
    token_gateway.set_valid_token(
        jwt_token, user_id, email, ["admin"], {"display_name": display_name}
    )

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = await use_case.execute(command)

    assert response.is_valid is True
    assert response.user_id == user_id
    assert response.email == email
    assert response.display_name == display_name
    assert response.session_id == session.id


@pytest.mark.asyncio
async def test_should_raise_exception_for_invalid_jwt_token(
    use_case: ValidateUserTokenUseCase,
):
    invalid_jwt_token = "invalid_jwt_token_xyz789"
    command = ValidateUserTokenCommand(jwt_token=invalid_jwt_token)

    with pytest.raises(InvalidTokenException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_raise_exception_for_expired_or_non_existent_session(
    use_case: ValidateUserTokenUseCase,
    token_gateway,
):
    jwt_token = "valid_jwt_token_but_no_session"

    # Setup valid JWT token but no session
    some_user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e1")
    token_gateway.set_valid_token(
        jwt_token, some_user_id, "user@lecoffre.com", ["user"], {}
    )

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    with pytest.raises(SessionNotFoundException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_raise_exception_when_user_no_longer_exists(
    use_case: ValidateUserTokenUseCase,
    token_gateway,
    session_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    jwt_token = "jwt_token_for_deleted_user"

    # Setup valid JWT token and session but no user
    token_gateway.set_valid_token(
        jwt_token, user_id, "deleted@lecoffre.com", ["admin"], {}
    )

    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    with pytest.raises(UserNotFoundException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_validate_token_with_admin_role(
    use_case: ValidateUserTokenUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"
    jwt_token = "jwt_token_for_admin@lecoffre.com_abc123"

    # Setup user password
    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash="hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    # Setup session
    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    # Setup JWT token validation with admin role
    token_gateway.set_valid_token(
        jwt_token, user_id, email, ["admin"], {"display_name": display_name}
    )

    command = ValidateUserTokenCommand(jwt_token=jwt_token, required_roles=["admin"])
    response = await use_case.execute(command)

    assert response.is_valid is True
    assert response.user_id == user_id
    assert response.email == email
    assert response.display_name == display_name
    assert response.session_id == session.id


@pytest.mark.asyncio
async def test_should_raise_exception_when_required_role_not_in_token(
    use_case: ValidateUserTokenUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@lecoffre.com"
    display_name = "Regular User"
    jwt_token = "jwt_token_for_user@lecoffre.com_abc123"

    # Setup user password
    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash="hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    # Setup session
    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    # Setup JWT token validation with only "user" role (missing "admin")
    token_gateway.set_valid_token(
        jwt_token, user_id, email, ["user"], {"display_name": display_name}
    )

    command = ValidateUserTokenCommand(jwt_token=jwt_token, required_roles=["admin"])

    with pytest.raises(InsufficientRoleException):
        await use_case.execute(command)
