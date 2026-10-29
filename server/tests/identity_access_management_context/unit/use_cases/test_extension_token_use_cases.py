"""Managing connected devices."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from identity_access_management_context.application.commands import (
    ListExtensionTokensCommand,
    RevokeAllExtensionTokensCommand,
    RevokeAllExtensionTokensForUserCommand,
    RevokeExtensionTokenCommand,
)
from identity_access_management_context.application.services import REVOCATION_REASON_ADMIN_REVOKED
from identity_access_management_context.application.use_cases import (
    ListExtensionTokensUseCase,
    RevokeAllExtensionTokensForUserUseCase,
    RevokeAllExtensionTokensUseCase,
    RevokeExtensionTokenUseCase,
)
from identity_access_management_context.domain.entities import TokenCredentialRecord, User
from identity_access_management_context.domain.events import ExtensionTokenRevokedEvent
from identity_access_management_context.domain.exceptions import (
    ExtensionTokenNotFoundError,
)
from identity_access_management_context.domain.value_objects import TokenCredential
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser, ValidatedUser

NOW = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
TOKEN_LIFETIME = timedelta(days=30)
COARSENING = 300
INACTIVITY = timedelta(days=14)


@pytest.fixture
def user():
    return ValidatedUser(user_id=uuid4(), email="alice@example.com", display_name="Alice", roles=["user"])


@pytest.fixture
def registered_user(user, user_repository):
    user_repository.save(
        User(
            id=user.user_id,
            username=user.email,
            email=user.email,
            name=user.display_name,
            roles=["user"],
        )
    )
    return user


@pytest.fixture
def list_use_case(token_credential_record_repository, time_provider):
    return ListExtensionTokensUseCase(
        token_credential_record_repository=token_credential_record_repository,
        time_provider=time_provider,
    )


@pytest.fixture
def revoke_use_case(token_credential_record_repository, event_publisher, admin_event_repository):
    return RevokeExtensionTokenUseCase(
        token_credential_record_repository=token_credential_record_repository,
        event_publisher=event_publisher,
        admin_event_repository=admin_event_repository,
    )


@pytest.fixture
def revoke_all_use_case(token_credential_record_repository, event_publisher, admin_event_repository):
    return RevokeAllExtensionTokensUseCase(
        token_credential_record_repository=token_credential_record_repository,
        event_publisher=event_publisher,
        admin_event_repository=admin_event_repository,
    )


@pytest.fixture
def revoke_all_for_user_use_case(token_credential_record_repository, event_publisher, admin_event_repository):
    return RevokeAllExtensionTokensForUserUseCase(
        token_credential_record_repository=token_credential_record_repository,
        event_publisher=event_publisher,
        admin_event_repository=admin_event_repository,
    )


def _issue(
    repository, user_id, now=NOW, device_name="Chrome on macOS"
) -> tuple[TokenCredential, TokenCredentialRecord]:
    token = TokenCredential.generate()
    record = TokenCredentialRecord(
        principal_id=user_id,
        token_hash=token.hash,
        read_only=True,
        label=device_name,
        expires_at=now + TOKEN_LIFETIME,
        last_used_at=now,
        max_idle=INACTIVITY,
    )
    repository.create([record])
    return token, record


class TestListDevices:
    def test_should_list_expired_devices_as_inactive_and_forget_revoked_ones(
        self, list_use_case, revoke_use_case, token_credential_record_repository, time_provider, user
    ):
        time_provider.set_current_time(NOW)
        _issue(token_credential_record_repository, user.user_id, device_name="Live")
        _issue(token_credential_record_repository, user.user_id, now=NOW - TOKEN_LIFETIME, device_name="Expired")
        _, revoked = _issue(token_credential_record_repository, user.user_id, device_name="Revoked")
        revoke_use_case.execute(RevokeExtensionTokenCommand(token_id=revoked.id, requesting_user=user))

        result = list_use_case.execute(ListExtensionTokensCommand(requesting_user=user))

        by_name = {token.device_name: token for token in result.tokens}
        assert by_name.keys() == {"Live", "Expired"}
        assert by_name["Live"].is_active is True
        assert by_name["Expired"].is_active is False

    def test_should_list_a_dormant_device_as_inactive(
        self, list_use_case, token_credential_record_repository, time_provider, user
    ):
        _issue(token_credential_record_repository, user.user_id, now=NOW - INACTIVITY, device_name="Drawer")
        _issue(token_credential_record_repository, user.user_id, device_name="Desk")
        time_provider.set_current_time(NOW)

        result = list_use_case.execute(ListExtensionTokensCommand(requesting_user=user))

        by_name = {token.device_name: token for token in result.tokens}
        assert by_name["Drawer"].is_active is False
        assert by_name["Desk"].is_active is True

    def test_should_omit_devices_when_they_belong_to_another_user(
        self, list_use_case, token_credential_record_repository, time_provider, user
    ):
        time_provider.set_current_time(NOW)
        _issue(token_credential_record_repository, uuid4())

        result = list_use_case.execute(ListExtensionTokensCommand(requesting_user=user))

        assert result.tokens == []


class TestRevoke:
    def test_should_disconnect_the_device_when_revoking(
        self, revoke_use_case, token_credential_record_repository, user
    ):
        _, record = _issue(token_credential_record_repository, user.user_id)

        revoke_use_case.execute(RevokeExtensionTokenCommand(token_id=record.id, requesting_user=user))

        assert token_credential_record_repository.get_by_id(record.id) is None

    def test_should_report_missing_when_the_device_belongs_to_another_user(
        self, revoke_use_case, token_credential_record_repository, user
    ):
        _, other = _issue(token_credential_record_repository, uuid4())

        with pytest.raises(ExtensionTokenNotFoundError):
            revoke_use_case.execute(RevokeExtensionTokenCommand(token_id=other.id, requesting_user=user))
        assert token_credential_record_repository.get_by_id(other.id) is not None

    def test_should_report_missing_when_revoking_twice(
        self, revoke_use_case, token_credential_record_repository, admin_event_repository, user
    ):
        _, record = _issue(token_credential_record_repository, user.user_id)
        command = RevokeExtensionTokenCommand(token_id=record.id, requesting_user=user)

        revoke_use_case.execute(command)
        with pytest.raises(ExtensionTokenNotFoundError):
            revoke_use_case.execute(command)

        revocation_events = [
            event for event in admin_event_repository.events if event["event_type"] == "ExtensionTokenRevokedEvent"
        ]
        # A second audit entry would be misleading: nothing changed.
        assert len(revocation_events) == 1

    def test_should_disconnect_every_device_when_revoking_all(
        self, revoke_all_use_case, token_credential_record_repository, user
    ):
        _issue(token_credential_record_repository, user.user_id)
        _issue(token_credential_record_repository, user.user_id)
        _, other = _issue(token_credential_record_repository, uuid4())

        revoked = revoke_all_use_case.execute(RevokeAllExtensionTokensCommand(requesting_user=user))

        assert revoked == 2
        assert token_credential_record_repository.get_by_id(other.id) is not None

    def test_should_record_nothing_when_there_was_nothing_to_revoke(
        self, revoke_all_use_case, admin_event_repository, user
    ):
        assert revoke_all_use_case.execute(RevokeAllExtensionTokensCommand(requesting_user=user)) == 0
        assert admin_event_repository.events == []


class TestAdminRevokeAll:
    """An administrator's lever for an account whose owner they cannot reach."""

    def test_should_disconnect_every_device_of_the_target_when_an_admin_asks(
        self, revoke_all_for_user_use_case, token_credential_record_repository, event_publisher, user
    ):
        admin = AuthenticatedUser(user_id=uuid4(), roles=["admin"])
        _issue(token_credential_record_repository, user.user_id)
        _issue(token_credential_record_repository, user.user_id)
        _, bystander = _issue(token_credential_record_repository, uuid4())

        revoked = revoke_all_for_user_use_case.execute(
            RevokeAllExtensionTokensForUserCommand(requesting_user=admin, target_user_id=user.user_id)
        )

        assert revoked == 2
        assert token_credential_record_repository.get_by_id(bystander.id) is not None
        event = next(e for e in event_publisher.published_events if isinstance(e, ExtensionTokenRevokedEvent))
        assert event.user_id == user.user_id
        assert event.reason == REVOCATION_REASON_ADMIN_REVOKED

    def test_should_record_the_admin_as_actor_and_the_user_as_owner(
        self, revoke_all_for_user_use_case, token_credential_record_repository, admin_event_repository, user
    ):
        # A row that conflated the two could answer neither "who did it" nor
        # "whose devices were cut".
        admin = AuthenticatedUser(user_id=uuid4(), roles=["admin"])
        _issue(token_credential_record_repository, user.user_id)

        revoke_all_for_user_use_case.execute(
            RevokeAllExtensionTokensForUserCommand(requesting_user=admin, target_user_id=user.user_id)
        )

        (entry,) = admin_event_repository.events
        assert entry["actor_principal_id"] == admin.user_id
        assert entry["event_data"]["user_id"] == str(user.user_id)

    def test_should_refuse_when_the_caller_is_not_an_admin(
        self, revoke_all_for_user_use_case, token_credential_record_repository, user
    ):
        _, record = _issue(token_credential_record_repository, user.user_id)
        someone = AuthenticatedUser(user_id=uuid4(), roles=["user"])

        with pytest.raises(NotAdminError):
            revoke_all_for_user_use_case.execute(
                RevokeAllExtensionTokensForUserCommand(requesting_user=someone, target_user_id=user.user_id)
            )

        assert token_credential_record_repository.get_by_id(record.id) is not None

    def test_should_report_zero_when_the_target_has_no_device(
        self, revoke_all_for_user_use_case, admin_event_repository
    ):
        admin = AuthenticatedUser(user_id=uuid4(), roles=["admin"])

        revoked = revoke_all_for_user_use_case.execute(
            RevokeAllExtensionTokensForUserCommand(requesting_user=admin, target_user_id=uuid4())
        )

        assert revoked == 0
        assert admin_event_repository.events == []
