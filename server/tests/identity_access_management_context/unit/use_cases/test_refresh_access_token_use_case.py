from datetime import timedelta
from uuid import UUID

import pytest

from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.application.gateways import (
    REVOCATION_REASON_LOGOUT,
    REVOCATION_REASON_REFRESH_TOKEN_ROTATED,
)
from identity_access_management_context.application.use_cases import (
    RefreshAccessTokenUseCase,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import FakeAuthSessionRepository, FakeRevokedTokenRepository, FakeTokenGateway, FakeUserRepository


@pytest.fixture
def use_case(
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider: FakeTimeGateway,
):
    return RefreshAccessTokenUseCase(
        token_gateway=token_gateway,
        user_repository=user_repository,
        auth_session_repository=auth_session_repository,
        revoked_token_repository=revoked_token_repository,
        time_provider=time_provider,
        session_max_lifetime_seconds=4 * 3600,
    )


def test_given_valid_refresh_token_when_execute_then_returns_new_access_token(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
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
    auth_session_repository.create_session(user_id, refresh_token_jti, FakeTimeGateway().get_current_time())

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti=refresh_token_jti)
    token_gateway.set_unique_jwt_part("new_access_token")

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act
    result = use_case.execute(command)

    # Assert
    assert result.access_token == f"jwt_token_for_{user_id}_new_access_token"
    assert result.refresh_token == f"refresh_token_for_{user_id}_new_access_token"
    assert result.user_id == user_id
    rotated_session = auth_session_repository.get_active_by_user_id_and_refresh_jti(
        user_id,
        "refresh-token-jti-new_access_token",
    )
    assert rotated_session is not None
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
    auth_session_repository: FakeAuthSessionRepository,
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
    auth_session_repository.create_session(user_id, refresh_token_jti, FakeTimeGateway().get_current_time())

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


# A jti that matches no active session (and is not revoked) is NOT a theft
# signal: it can be a token whose session was purged, or the thief's own
# rotated-forward token after reuse containment already killed the session.
# This path must therefore stay a plain rejection without any escalation —
# containment only triggers on a replayed jti revoked for rotation (see
# test_given_replayed_rotated_refresh_token_... below).
def test_given_refresh_token_jti_not_matching_active_session_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
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
    auth_session_repository.create_session(user_id, "active-refresh-token-jti", time_provider.get_current_time())

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)

    unchanged_user = user_repository.get_by_id(user_id)
    assert unchanged_user is not None
    assert unchanged_user.current_refresh_token_jti == "active-refresh-token-jti"
    assert unchanged_user.session_invalid_before is None
    assert revoked_token_repository.is_revoked("stale-refresh-token-jti", now=time_provider.get_current_time()) is False


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


def test_given_replayed_rotated_refresh_token_when_execute_then_invalidates_all_sessions_and_sets_cutoff(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider: FakeTimeGateway,
):
    # Arrange: a thief stole the victim's refresh token and rotated it first —
    # the session now points at the thief's jti, the stolen jti is revoked
    # with the rotation reason. The victim then replays the stolen token.
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    replayed_refresh_token = "stolen_refresh_token"
    replayed_jti = "stolen-refresh-token-jti"
    attacker_jti = "attacker-rotated-refresh-token-jti"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
        )
    )
    auth_session_repository.create_session(user_id, attacker_jti, time_provider.get_current_time())
    revoked_token_repository.revoke_jti(
        replayed_jti,
        expires_at=None,
        reason=REVOCATION_REASON_REFRESH_TOKEN_ROTATED,
    )
    token_gateway.set_valid_refresh_token(replayed_refresh_token, user_id, email, roles, jti=replayed_jti)

    command = RefreshAccessTokenCommand(refresh_token=replayed_refresh_token)

    # Act & Assert: generic rejection, but the whole family is contained
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)

    assert auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, attacker_jti) is None
    contained_user = user_repository.get_by_id(user_id)
    assert contained_user is not None
    # The cutoff must be the exact (non-truncated) detection time so the
    # thief's same-second access token fails `issued_at < cutoff`.
    assert contained_user.session_invalid_before == time_provider.get_current_time()


def test_given_replayed_logged_out_refresh_token_when_execute_then_raises_without_containment(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider: FakeTimeGateway,
):
    # Arrange: an in-flight refresh replaying a token revoked by a normal
    # logout is benign — it must not log the user out of their other devices.
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    replayed_refresh_token = "logged_out_refresh_token"
    replayed_jti = "logged-out-refresh-token-jti"
    other_device_jti = "other-device-refresh-token-jti"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
        )
    )
    auth_session_repository.create_session(user_id, other_device_jti, time_provider.get_current_time())
    revoked_token_repository.revoke_jti(replayed_jti, expires_at=None, reason=REVOCATION_REASON_LOGOUT)
    token_gateway.set_valid_refresh_token(replayed_refresh_token, user_id, email, roles, jti=replayed_jti)

    command = RefreshAccessTokenCommand(refresh_token=replayed_refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)

    assert auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, other_device_jti) is not None
    unchanged_user = user_repository.get_by_id(user_id)
    assert unchanged_user is not None
    assert unchanged_user.session_invalid_before is None


def test_given_concurrent_rotation_wins_the_race_when_execute_then_raises_without_revoking(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider: FakeTimeGateway,
):
    # Arrange: two concurrent refreshes with the same token — the loser's
    # compare-and-swap matches zero rows. It must reject without revoking the
    # jti (the winner already did) and without any containment.
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "raced_refresh_token"
    refresh_token_jti = "raced-refresh-token-jti"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
        )
    )
    auth_session_repository.create_session(user_id, refresh_token_jti, time_provider.get_current_time())
    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti=refresh_token_jti)

    # Simulate the concurrent winner committing between the session lookup and
    # the compare-and-swap.
    auth_session_repository.rotate_refresh_token_jti = lambda **_kwargs: False

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)

    assert revoked_token_repository.is_revoked(refresh_token_jti, now=time_provider.get_current_time()) is False
    unchanged_user = user_repository.get_by_id(user_id)
    assert unchanged_user is not None
    assert unchanged_user.session_invalid_before is None


def test_given_session_older_than_max_lifetime_when_execute_then_raises_and_invalidates_session(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider: FakeTimeGateway,
):
    # Arrange: an otherwise-valid session that reached the absolute lifetime cap
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "aged_refresh_token"
    refresh_token_jti = "aged-refresh-token-jti"
    now = time_provider.get_current_time()

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
        )
    )
    auth_session_repository.create_session(user_id, refresh_token_jti, now - timedelta(hours=4))
    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti=refresh_token_jti)

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act & Assert: generic rejection, session invalidated, no theft escalation
    with pytest.raises(InvalidRefreshTokenException):
        use_case.execute(command)

    assert auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, refresh_token_jti) is None
    unchanged_user = user_repository.get_by_id(user_id)
    assert unchanged_user is not None
    assert unchanged_user.session_invalid_before is None
    assert revoked_token_repository.is_revoked(refresh_token_jti, now=now) is False


def test_given_session_just_under_max_lifetime_when_execute_then_returns_new_tokens(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
    time_provider: FakeTimeGateway,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "almost_aged_refresh_token"
    refresh_token_jti = "almost-aged-refresh-token-jti"
    now = time_provider.get_current_time()

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
        )
    )
    auth_session_repository.create_session(user_id, refresh_token_jti, now - timedelta(hours=4) + timedelta(seconds=1))
    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti=refresh_token_jti)
    token_gateway.set_unique_jwt_part("under_lifetime_cap")

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act
    result = use_case.execute(command)

    # Assert
    assert result.refresh_token == f"refresh_token_for_{user_id}_under_lifetime_cap"


def test_given_stale_sessions_when_execute_then_purges_sessions_older_than_refresh_ttl(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
    time_provider: FakeTimeGateway,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "valid_refresh_token_123"
    refresh_token_jti = "refresh-token-jti-1"
    now = time_provider.get_current_time()

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
        )
    )
    auth_session_repository.create_session(user_id, refresh_token_jti, now)
    # A session idle for longer than the refresh TTL holds a token that can no
    # longer be used — it must be purged on the next refresh write path.
    stale_session = auth_session_repository.create_session(user_id, "stale-refresh-token-jti", now - timedelta(hours=5))
    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti=refresh_token_jti)
    token_gateway.set_unique_jwt_part("after_purge")

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act
    use_case.execute(command)

    # Assert
    assert auth_session_repository.purge_dead_cutoffs == [now - timedelta(hours=4)]
    assert stale_session.id not in auth_session_repository.sessions


def test_given_two_active_sessions_when_one_session_rotates_then_other_session_remains_valid(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    auth_session_repository: FakeAuthSessionRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]

    refresh_token_a = "refresh_token_device_a"
    refresh_token_b = "refresh_token_device_b"
    refresh_jti_a = "refresh-jti-device-a"
    refresh_jti_b = "refresh-jti-device-b"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
        )
    )

    auth_session_repository.create_session(user_id, refresh_jti_a, FakeTimeGateway().get_current_time())
    auth_session_repository.create_session(user_id, refresh_jti_b, FakeTimeGateway().get_current_time())

    token_gateway.set_valid_refresh_token(refresh_token_a, user_id, email, roles, jti=refresh_jti_a)
    token_gateway.set_valid_refresh_token(refresh_token_b, user_id, email, roles, jti=refresh_jti_b)

    token_gateway.set_unique_jwt_part("device-a")
    result_a = use_case.execute(RefreshAccessTokenCommand(refresh_token=refresh_token_a))
    assert result_a.refresh_token == f"refresh_token_for_{user_id}_device-a"

    token_gateway.set_unique_jwt_part("device-b")
    result_b = use_case.execute(RefreshAccessTokenCommand(refresh_token=refresh_token_b))
    assert result_b.refresh_token == f"refresh_token_for_{user_id}_device-b"
