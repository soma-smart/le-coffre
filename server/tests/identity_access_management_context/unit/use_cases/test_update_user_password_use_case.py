from datetime import timedelta
from uuid import UUID

import pytest

from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.application.use_cases import (
    UpdateUserPasswordUseCase,
)
from identity_access_management_context.domain.entities import ExtensionToken, User, UserPassword
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import ExtensionTokenSecret
from tests.identity_access_management_context.unit.fakes import (
    FakePasswordHashingGateway,
    FakeTokenGateway,
    FakeUserPasswordRepository,
    FakeUserRepository,
)
from tests.shared_kernel.fakes import FakeTimeGateway


@pytest.fixture
def use_case(
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    user_repository: FakeUserRepository,
    auth_session_repository,
    token_gateway: FakeTokenGateway,
    time_provider: FakeTimeGateway,
    extension_token_repository,
    domain_event_publisher,
    admin_event_repository,
):
    return UpdateUserPasswordUseCase(
        user_password_repository,
        password_hashing_gateway,
        user_repository,
        auth_session_repository,
        token_gateway,
        time_provider,
        extension_token_repository,
        domain_event_publisher,
        admin_event_repository,
    )


def test_given_valid_user_with_correct_old_password_when_updating_password_should_update_successfully(
    use_case: UpdateUserPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    user_repository: FakeUserRepository,
    auth_session_repository,
    token_gateway: FakeTokenGateway,
    time_provider: FakeTimeGateway,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"

    # Create existing user with hashed old password
    user_password = UserPassword(
        id=user_id,
        email="user@example.com",
        password_hash=password_hashing_gateway.hash(old_password),
        display_name="Test User",
    )
    user_password_repository.save(user_password)
    user_repository.save(
        User(
            id=user_id,
            username="testuser",
            email="user@example.com",
            name="Test User",
            roles=["user"],
            current_refresh_token_jti="active-refresh-token-jti",
        )
    )
    existing_session = auth_session_repository.create_session(
        user_id,
        "refresh-token-jti-before-password-change",
        time_provider.get_current_time(),
    )

    command = UpdateUserPasswordCommand(
        user_id=user_id,
        old_password=old_password,
        new_password=new_password,
    )

    # Act
    token_gateway.set_unique_jwt_part("password-change")
    result = use_case.execute(command)

    # Assert
    updated_user = user_password_repository.get_by_id(user_id)
    assert updated_user is not None
    assert password_hashing_gateway.verify(new_password, updated_user.password_hash)
    assert not password_hashing_gateway.verify(old_password, updated_user.password_hash)
    authenticated_user = user_repository.get_by_id(user_id)
    assert authenticated_user is not None
    assert authenticated_user.session_invalid_before == time_provider.get_current_time().replace(microsecond=0)

    stale_session = auth_session_repository.sessions[existing_session.id]
    assert stale_session.invalidated_at == time_provider.get_current_time().replace(microsecond=0)
    current_session = auth_session_repository.get_active_by_user_id_and_refresh_jti(
        user_id,
        "refresh-token-jti-password-change",
    )
    assert current_session is not None

    assert result.access_token == f"jwt_token_for_{user_id}_password-change"
    assert result.refresh_token == f"refresh_token_for_{user_id}_password-change"


def test_given_incorrect_old_password_when_updating_password_should_raise_invalid_credentials(
    use_case: UpdateUserPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    actual_password = "ActualPassword123!"
    wrong_old_password = "WrongPassword123!"
    new_password = "NewPassword456!"

    # Create existing user with hashed password
    user_password = UserPassword(
        id=user_id,
        email="user@example.com",
        password_hash=password_hashing_gateway.hash(actual_password),
        display_name="Test User",
    )
    user_password_repository.save(user_password)

    command = UpdateUserPasswordCommand(
        user_id=user_id,
        old_password=wrong_old_password,
        new_password=new_password,
    )

    # Act & Assert
    with pytest.raises(InvalidCredentialsException):
        use_case.execute(command)


def test_given_user_not_in_password_repository_when_updating_password_should_raise_user_not_found(
    use_case: UpdateUserPasswordUseCase,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    command = UpdateUserPasswordCommand(
        user_id=user_id,
        old_password="OldPassword123!",
        new_password="NewPassword456!",
    )

    # Act & Assert
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_given_password_record_exists_but_user_missing_when_updating_password_then_does_not_persist_new_password(
    use_case: UpdateUserPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"

    user_password_repository.save(
        UserPassword(
            id=user_id,
            email="user@example.com",
            password_hash=password_hashing_gateway.hash(old_password),
            display_name="Test User",
        )
    )

    command = UpdateUserPasswordCommand(
        user_id=user_id,
        old_password=old_password,
        new_password=new_password,
    )

    with pytest.raises(UserNotFoundException):
        use_case.execute(command)

    unchanged_user_password = user_password_repository.get_by_id(user_id)
    assert unchanged_user_password is not None
    assert password_hashing_gateway.verify(old_password, unchanged_user_password.password_hash)
    assert not password_hashing_gateway.verify(new_password, unchanged_user_password.password_hash)


def test_given_paired_extensions_when_password_changes_then_revokes_them_outright(
    use_case: UpdateUserPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    extension_token_repository,
    time_provider: FakeTimeGateway,
):
    """Revoked on the row, not merely shadowed by session_invalid_before.

    The cutoff alone did stop an extension token authenticating, but it left
    revoked_at empty, so `is_active` stayed true. Two things read the row rather
    than the cutoff and both then lied: the "Connected extensions" screen listed
    a dead credential as live, and the rate limiter kept charging its requests
    to this user's per-user bucket, which a thief holding the dead token could
    burn at the victim's expense.
    """
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    now = time_provider.get_current_time()

    user_repository.save(User(id=user_id, username="u", email="u@example.com", name="U"))
    user_password_repository.save(
        UserPassword(
            id=user_id,
            email="u@example.com",
            display_name="U",
            password_hash=password_hashing_gateway.hash("old-password-long-enough"),
        )
    )
    extension_token_repository.add(
        ExtensionToken.create(
            user_id=user_id,
            secret=ExtensionTokenSecret.generate(),
            device_name="Browser extension",
            lifetime=timedelta(days=30),
            now=now,
        )
    )
    assert extension_token_repository.count_active_for_user(user_id, now) == 1

    use_case.execute(
        UpdateUserPasswordCommand(
            user_id=user_id,
            old_password="old-password-long-enough",
            new_password="new-password-long-enough",
        )
    )

    assert extension_token_repository.count_active_for_user(user_id, now) == 0
    stored = extension_token_repository.list_for_user(user_id)[0]
    assert stored.revoked_at is not None
