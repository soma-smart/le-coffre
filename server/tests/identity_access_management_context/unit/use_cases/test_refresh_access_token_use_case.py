from uuid import UUID

import pytest

from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.application.use_cases import (
    RefreshAccessTokenUseCase,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import FakeRevokedTokenRepository, FakeTokenGateway, FakeUserRepository


@pytest.fixture
def use_case(
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider: FakeTimeGateway,
):
    return RefreshAccessTokenUseCase(
        token_gateway=token_gateway,
        user_repository=user_repository,
        revoked_token_repository=revoked_token_repository,
        time_provider=time_provider,
    )


def test_given_valid_refresh_token_when_execute_then_returns_new_access_token(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "valid_refresh_token_123"
    refresh_token_jti = "refresh-token-jti-1"

    user = User(
        id=user_id,
        username="testuser",
        email=email,
        name="Test User",
        roles=roles,
        current_refresh_token_jti=refresh_token_jti,
    )
    user_repository.save(user)

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti=refresh_token_jti)
    token_gateway.set_unique_jwt_part("new_access_token")

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act
    result = use_case.execute(command)

    # Assert
    assert result.access_token == f"jwt_token_for_{user_id}_new_access_token"
    assert result.refresh_token == f"refresh_token_for_{user_id}_new_access_token"
    assert result.user_id == user_id
    updated_user = user_repository.get_by_id(user_id)
    assert updated_user is not None
    assert updated_user.current_refresh_token_jti == "refresh-token-jti-new_access_token"
    assert revoked_token_repository.is_revoked(refresh_token_jti, now=FakeTimeGateway().get_current_time()) is True
    assert revoked_token_repository.purge_calls == 1


def test_given_invalid_refresh_token_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
):
    # Arrange
    invalid_refresh_token = "invalid_token_xyz"
    command = RefreshAccessTokenCommand(refresh_token=invalid_refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)


def test_given_revoked_refresh_token_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider: FakeTimeGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "revoked_refresh_token"
    refresh_token_jti = "revoked-refresh-token-jti"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
            current_refresh_token_jti=refresh_token_jti,
        )
    )
    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti=refresh_token_jti)
    revoked_token_repository.revoke_jti(refresh_token_jti, expires_at=None)

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)


def test_given_refresh_token_without_jti_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "refresh_token_without_jti"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
            current_refresh_token_jti="current-refresh-token-jti",
        )
    )

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti="token-jti")
    token_gateway.valid_refresh_tokens[refresh_token].jti = None

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)


def test_given_refresh_token_without_issued_at_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "refresh_token_without_issued_at"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
            current_refresh_token_jti="current-refresh-token-jti",
        )
    )

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti="token-jti")
    token_gateway.valid_refresh_tokens[refresh_token].issued_at = None

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)


def test_given_expired_refresh_token_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
):
    # Arrange
    expired_refresh_token = "expired_token_abc"
    command = RefreshAccessTokenCommand(refresh_token=expired_refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)


def test_given_refresh_token_for_nonexistent_user_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "deleted@example.com"
    roles = ["user"]
    refresh_token = "valid_token_for_deleted_user"

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles)
    # User does not exist in repository (not added)

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)


def test_given_user_promoted_to_admin_when_refresh_token_then_new_token_has_updated_roles(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "promoted@example.com"

    # User initially has only "user" role
    old_roles = ["user"]
    refresh_token = "valid_refresh_token_before_promotion"
    refresh_token_jti = "refresh-token-jti-before-promotion"

    # Create user with initial roles
    user = User(
        id=user_id,
        username="promoted_user",
        email=email,
        name="Promoted User",
        roles=old_roles,
        current_refresh_token_jti=refresh_token_jti,
    )
    user_repository.save(user)

    # Refresh token was issued with old roles
    token_gateway.set_valid_refresh_token(
        refresh_token,
        user_id,
        email,
        old_roles,
        jti=refresh_token_jti,
    )

    # User gets promoted to admin (roles updated in database)
    user.promote_to_admin()
    user_repository.update(user)

    # Get updated user from repository to verify promotion
    updated_user = user_repository.get_by_id(user_id)
    assert "admin" in updated_user.roles, "User should have admin role in database"

    token_gateway.set_unique_jwt_part("new_token_after_promotion")

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act
    result = use_case.execute(command)

    # Assert
    assert result.access_token == f"jwt_token_for_{user_id}_new_token_after_promotion"

    # Verify that the new token was generated with CURRENT roles from database
    # (not with stale roles from the old refresh token)
    last_generated_token = token_gateway.get_last_generated_token()
    assert last_generated_token is not None, "Token should have been generated"
    assert "admin" in last_generated_token.roles, "New access token should include admin role from database"
    assert last_generated_token.roles == ["user", "admin"], (
        "New access token should have current roles: ['user', 'admin']"
    )


def test_given_refresh_token_jti_not_matching_active_session_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider: FakeTimeGateway,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "stale_refresh_token"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
            current_refresh_token_jti="active-refresh-token-jti",
        )
    )

    token_gateway.set_valid_refresh_token(
        refresh_token,
        user_id,
        email,
        roles,
        jti="stale-refresh-token-jti",
    )

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)

    compromised_user = user_repository.get_by_id(user_id)
    assert compromised_user is not None
    assert compromised_user.current_refresh_token_jti is None
    assert compromised_user.session_invalid_before == time_provider.get_current_time().replace(microsecond=0)
    assert revoked_token_repository.is_revoked("stale-refresh-token-jti", now=time_provider.get_current_time()) is True


def test_given_refresh_token_issued_microseconds_before_session_cutoff_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "microsecond_before_cutoff_refresh_token"
    refresh_token_jti = "refresh-token-jti-microsecond-before-cutoff"

    session_cutoff = FakeTimeGateway().get_current_time().replace(microsecond=500000)
    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
            current_refresh_token_jti=refresh_token_jti,
            session_invalid_before=session_cutoff,
        )
    )

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti=refresh_token_jti)
    token_gateway.valid_refresh_tokens[refresh_token].issued_at = session_cutoff.replace(microsecond=499999)

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)
