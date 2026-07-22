from uuid import UUID

import pytest

from identity_access_management_context.application.commands import LogoutCommand
from identity_access_management_context.application.use_cases import LogoutUseCase
from identity_access_management_context.domain.entities import User

from ..fakes import FakeRevokedTokenRepository, FakeTokenGateway, FakeUserRepository


@pytest.fixture
def use_case(
    token_gateway: FakeTokenGateway,
    revoked_token_repository: FakeRevokedTokenRepository,
    user_repository: FakeUserRepository,
    time_provider,
):
    return LogoutUseCase(
        token_gateway=token_gateway,
        revoked_token_repository=revoked_token_repository,
        user_repository=user_repository,
        time_provider=time_provider,
    )


def test_given_valid_access_and_refresh_tokens_when_logout_then_revoke_tokens_and_clear_active_refresh_jti(
    use_case: LogoutUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    access_token = "valid_access_token"
    refresh_token = "valid_refresh_token"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
            current_refresh_token_jti="refresh-jti-1",
        )
    )
    token_gateway.set_valid_token(access_token, user_id, email, roles, jti="access-jti-1")
    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti="refresh-jti-1")

    use_case.execute(
        LogoutCommand(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )

    updated_user = user_repository.get_by_id(user_id)
    assert updated_user is not None
    assert updated_user.current_refresh_token_jti is None

    now = time_provider.get_current_time()
    assert revoked_token_repository.is_revoked("access-jti-1", now=now) is True
    assert revoked_token_repository.is_revoked("refresh-jti-1", now=now) is True
    assert revoked_token_repository.purge_calls == 1


def test_given_invalid_access_and_valid_refresh_tokens_when_logout_then_clear_active_refresh_jti(
    use_case: LogoutUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    revoked_token_repository: FakeRevokedTokenRepository,
    time_provider,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    access_token = "invalid_access_token"
    refresh_token = "valid_refresh_token"

    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email=email,
            name="Test User",
            roles=roles,
            current_refresh_token_jti="refresh-jti-1",
        )
    )
    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles, jti="refresh-jti-1")

    use_case.execute(LogoutCommand(access_token=access_token, refresh_token=refresh_token))

    updated_user = user_repository.get_by_id(user_id)
    assert updated_user is not None
    assert updated_user.current_refresh_token_jti is None

    assert revoked_token_repository.is_revoked("refresh-jti-1", now=time_provider.get_current_time()) is True


def test_given_invalid_tokens_when_logout_then_do_nothing(
    use_case: LogoutUseCase,
    user_repository: FakeUserRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email="user@example.com",
            name="Test User",
            roles=["user"],
            current_refresh_token_jti="refresh-jti-1",
        )
    )

    use_case.execute(LogoutCommand(access_token="invalid_access_token", refresh_token="invalid_refresh_token"))

    unchanged_user = user_repository.get_by_id(user_id)
    assert unchanged_user is not None
    assert unchanged_user.current_refresh_token_jti == "refresh-jti-1"
