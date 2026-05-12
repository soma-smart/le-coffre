from uuid import UUID

import pytest

from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.use_cases import (
    ValidateUserTokenUseCase,
)
from identity_access_management_context.domain.entities import (
    SsoUser,
    UserPassword,
)
from identity_access_management_context.domain.exceptions import (
    InsufficientRoleException,
    InvalidTokenException,
    UserNotFoundException,
)

from ..fakes import FakeSsoUserRepository, FakeTokenGateway, FakeUserPasswordRepository


@pytest.fixture
def use_case(
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
    sso_user_repository: FakeSsoUserRepository,
):
    return ValidateUserTokenUseCase(user_password_repository, token_gateway, sso_user_repository)


def test_should_validate_token_and_return_user_details(
    use_case: ValidateUserTokenUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"
    jwt_token = "jwt_token_for_admin@lecoffre.com_abc123"

    # Setup user password
    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash=b"hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    # Setup JWT token validation
    token_gateway.set_valid_token(jwt_token, user_id, email, ["admin"], {"display_name": display_name})

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = use_case.execute(command)

    assert response.is_valid is True
    assert response.user_id == user_id
    assert response.email == email
    assert response.display_name == display_name


def test_should_raise_exception_for_invalid_jwt_token(
    use_case: ValidateUserTokenUseCase,
):
    invalid_jwt_token = "invalid_jwt_token_xyz789"
    command = ValidateUserTokenCommand(jwt_token=invalid_jwt_token)

    with pytest.raises(InvalidTokenException):
        use_case.execute(command)


def test_should_raise_exception_when_user_no_longer_exists(
    use_case: ValidateUserTokenUseCase,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    jwt_token = "jwt_token_for_deleted_user"

    # Setup valid JWT token but no user
    token_gateway.set_valid_token(jwt_token, user_id, "deleted@lecoffre.com", ["admin"], {})

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_should_validate_token_with_admin_role(
    use_case: ValidateUserTokenUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"
    jwt_token = "jwt_token_for_admin@lecoffre.com_abc123"

    # Setup user password
    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash=b"hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    # Setup JWT token validation with admin role
    token_gateway.set_valid_token(jwt_token, user_id, email, ["admin"], {"display_name": display_name})

    command = ValidateUserTokenCommand(jwt_token=jwt_token, required_roles=["admin"])
    response = use_case.execute(command)

    assert response.is_valid is True
    assert response.user_id == user_id
    assert response.email == email
    assert response.display_name == display_name


def test_should_raise_exception_when_required_role_not_in_token(
    use_case: ValidateUserTokenUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@lecoffre.com"
    display_name = "Regular User"
    jwt_token = "jwt_token_for_user@lecoffre.com_abc123"

    # Setup user password
    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash=b"hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    # Setup JWT token validation with only "user" role (missing "admin")
    token_gateway.set_valid_token(jwt_token, user_id, email, ["user"], {"display_name": display_name})

    command = ValidateUserTokenCommand(jwt_token=jwt_token, required_roles=["admin"])

    with pytest.raises(InsufficientRoleException):
        use_case.execute(command)


def test_should_validate_token_for_sso_user(
    use_case: ValidateUserTokenUseCase,
    sso_user_repository: FakeSsoUserRepository,
    token_gateway: FakeTokenGateway,
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
    sso_user_repository.create(sso_user)

    # Setup JWT token validation
    token_gateway.set_valid_token(jwt_token, user_id, email, ["user"], {"display_name": display_name})

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = use_case.execute(command)

    assert response.is_valid is True
    assert response.user_id == user_id
    assert response.email == email
    assert response.display_name == display_name


def test_should_raise_exception_when_sso_user_not_found(
    use_case: ValidateUserTokenUseCase,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e6")
    email = "nonexistent_sso@example.com"
    jwt_token = "jwt_token_for_nonexistent_sso_user"

    # Setup valid JWT token but no SSO user
    token_gateway.set_valid_token(jwt_token, user_id, email, ["user"], {})

    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_should_return_admin_roles_for_admin_user_token(
    use_case: ValidateUserTokenUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
):
    # Given an admin user with password authentication and JWT containing ["admin"] role
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"
    jwt_token = "jwt_token_for_admin@lecoffre.com_abc123"

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash=b"hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    token_gateway.set_valid_token(jwt_token, user_id, email, ["admin"], {"display_name": display_name})

    # When validating the token
    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = use_case.execute(command)

    # Then response should include roles=["admin"]
    assert response.roles == ["admin"]


def test_should_return_multiple_roles_when_token_has_multiple_roles(
    use_case: ValidateUserTokenUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
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
        password_hash=b"hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    token_gateway.set_valid_token(jwt_token, user_id, email, roles, {"display_name": display_name})

    # When validating the token
    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = use_case.execute(command)

    # Then response should include roles=["user", "editor", "viewer"]
    assert response.roles == roles


def test_should_return_empty_roles_when_token_has_no_roles(
    use_case: ValidateUserTokenUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
):
    # Given a user with JWT containing empty roles list
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "no_role@lecoffre.com"
    display_name = "No Role User"
    jwt_token = "jwt_token_for_no_role@lecoffre.com_abc"

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash=b"hashed_password",
        display_name=display_name,
    )
    user_password_repository.save(user_password)

    token_gateway.set_valid_token(jwt_token, user_id, email, [], {"display_name": display_name})

    # When validating the token
    command = ValidateUserTokenCommand(jwt_token=jwt_token)
    response = use_case.execute(command)

    # Then response should include roles=[]
    assert response.roles == []
