import pytest
from uuid import UUID
from datetime import datetime, UTC, timedelta

from identity_access_management_context.application.use_cases import (
    ValidateUserTokenUseCase,
)
from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.domain.entities import (
    UserPassword,
    AuthenticationSession,
    SsoUser,
)
from identity_access_management_context.domain.exceptions import (
    InvalidTokenException,
    SessionNotFoundException,
    UserNotFoundException,
    InsufficientRoleException,
)


@pytest.fixture
def use_case(
    user_password_repository, token_gateway, session_repository, sso_user_repository
):
    return ValidateUserTokenUseCase(
        user_password_repository, token_gateway, session_repository, sso_user_repository
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


@pytest.mark.asyncio
async def test_should_validate_token_for_sso_user(
    use_case: ValidateUserTokenUseCase,
    sso_user_repository,
    token_gateway,
    session_repository,
):
    user_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e6")
    email = "sso_user@example.com"
    display_name = "SSO User"
    jwt_token = "jwt_token_for_sso_user@example.com_xyz789"

    # Setup SSO user
    sso_user = SsoUser(
        internal_user_id=user_id,
        email=email,
        display_name=display_name,
        sso_user_id="sso_123456",
        sso_provider="default",
    )
    sso_user_repository.save(sso_user)

    # Setup session
    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    # Setup JWT token validation
    token_gateway.set_valid_token(
        jwt_token, user_id, email, ["user"], {"display_name": display_name}
    )

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = await use_case.execute(command)

    assert response.is_valid is True
    assert response.user_id == user_id
    assert response.email == email
    assert response.display_name == display_name
    assert response.session_id == session.id


@pytest.mark.asyncio
async def test_should_raise_exception_when_sso_user_not_found(
    use_case: ValidateUserTokenUseCase,
    token_gateway,
    session_repository,
):
    user_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e6")
    email = "nonexistent_sso@example.com"
    jwt_token = "jwt_token_for_nonexistent_sso_user"

    # Setup valid JWT token and session but no SSO user
    token_gateway.set_valid_token(jwt_token, user_id, email, ["user"], {})

    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    with pytest.raises(UserNotFoundException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_return_admin_roles_for_admin_user_token(
    use_case: ValidateUserTokenUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    # Given an admin user with password authentication and JWT containing ["admin"] role
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"
    jwt_token = "jwt_token_for_admin@lecoffre.com_abc123"

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash="hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    token_gateway.set_valid_token(
        jwt_token, user_id, email, ["admin"], {"display_name": display_name}
    )

    # When validating the token
    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = await use_case.execute(command)

    # Then response should include roles=["admin"]
    assert response.roles == ["admin"]


@pytest.mark.asyncio
async def test_should_return_multiple_roles_when_token_has_multiple_roles(
    use_case: ValidateUserTokenUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    # Given a user with JWT containing ["user", "editor", "viewer"] roles
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "multi_role@lecoffre.com"
    display_name = "Multi Role User"
    jwt_token = "jwt_token_for_multi_role@lecoffre.com_xyz"
    roles = ["user", "editor", "viewer"]

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash="hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    token_gateway.set_valid_token(
        jwt_token, user_id, email, roles, {"display_name": display_name}
    )

    # When validating the token
    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = await use_case.execute(command)

    # Then response should include roles=["user", "editor", "viewer"]
    assert response.roles == roles


@pytest.mark.asyncio
async def test_should_return_empty_roles_when_token_has_no_roles(
    use_case: ValidateUserTokenUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    # Given a user with JWT containing empty roles list
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "no_role@lecoffre.com"
    display_name = "No Role User"
    jwt_token = "jwt_token_for_no_role@lecoffre.com_abc"

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash="hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session_repository.save(session)

    token_gateway.set_valid_token(
        jwt_token, user_id, email, [], {"display_name": display_name}
    )

    # When validating the token
    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = await use_case.execute(command)

    # Then response should include roles=[]
    assert response.roles == []


@pytest.mark.asyncio
async def test_given_expired_session_when_validate_token_then_session_is_deleted(
    use_case: ValidateUserTokenUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    # Given an expired session (created 25 hours ago with default 24-hour TTL)
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "expired@lecoffre.com"
    display_name = "Expired User"
    jwt_token = "jwt_token_for_expired_session"

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash="hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    # Create session with past created_at to simulate expiration
    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session.created_at = datetime.now(UTC) - timedelta(hours=25)
    session.expires_at = session.created_at + timedelta(hours=24)
    session_repository.save(session)

    token_gateway.set_valid_token(
        jwt_token, user_id, email, ["user"], {"display_name": display_name}
    )

    # When validating the token
    command = ValidateUserTokenCommand(jwt_token=jwt_token)

    try:
        await use_case.execute(command)
    except SessionNotFoundException:
        pass

    # Then the session should be deleted from repository
    deleted_session = session_repository.get_by_token(jwt_token)
    assert deleted_session is None


@pytest.mark.asyncio
async def test_given_expired_session_when_validate_token_then_session_not_found_exception_raised(
    use_case: ValidateUserTokenUseCase,
    user_password_repository,
    token_gateway,
    session_repository,
):
    # Given an expired session (created 25 hours ago with default 24-hour TTL)
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "expired@lecoffre.com"
    display_name = "Expired User"
    jwt_token = "jwt_token_for_expired_session_2"

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash="hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    # Create session with past created_at to simulate expiration
    session = AuthenticationSession(user_id=user_id, jwt_token=jwt_token)
    session.created_at = datetime.now(UTC) - timedelta(hours=25)
    session.expires_at = session.created_at + timedelta(hours=24)
    session_repository.save(session)

    token_gateway.set_valid_token(
        jwt_token, user_id, email, ["user"], {"display_name": display_name}
    )

    # When validating the token
    command = ValidateUserTokenCommand(jwt_token=jwt_token)

    # Then SessionNotFoundException should be raised with "Session expired" message
    with pytest.raises(SessionNotFoundException, match="Session expired"):
        await use_case.execute(command)
