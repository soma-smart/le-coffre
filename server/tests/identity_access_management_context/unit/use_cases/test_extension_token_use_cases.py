"""Validating a bearer credential, and managing connected devices."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from identity_access_management_context.application.commands import (
    ListExtensionTokensCommand,
    RevokeAllExtensionTokensCommand,
    RevokeExtensionTokenCommand,
    ValidateExtensionTokenCommand,
)
from identity_access_management_context.application.use_cases import (
    ListExtensionTokensUseCase,
    RevokeAllExtensionTokensUseCase,
    RevokeExtensionTokenUseCase,
    ValidateExtensionTokenUseCase,
)
from identity_access_management_context.domain.entities import ExtensionToken, User, UserPassword
from identity_access_management_context.domain.exceptions import (
    ExtensionTokenExpiredError,
    ExtensionTokenNotFoundError,
    ExtensionTokenRevokedError,
)
from identity_access_management_context.domain.value_objects import ExtensionTokenSecret
from shared_kernel.domain.entities import ValidatedUser

NOW = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
TOKEN_LIFETIME = timedelta(days=30)
COARSENING = 300


@pytest.fixture
def user():
    return ValidatedUser(user_id=uuid4(), email="alice@example.com", display_name="Alice", roles=["user"])


@pytest.fixture
def registered_user(user, user_password_repository, user_repository):
    user_password_repository.save(
        UserPassword(
            id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            password_hash=b"hashed",
        )
    )
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
def validate_use_case(
    extension_token_repository, user_password_repository, sso_user_repository, user_repository, time_provider
):
    time_provider.set_current_time(NOW)
    return ValidateExtensionTokenUseCase(
        extension_token_repository=extension_token_repository,
        user_password_repository=user_password_repository,
        sso_user_repository=sso_user_repository,
        user_repository=user_repository,
        time_provider=time_provider,
        last_used_coarsening_seconds=COARSENING,
    )


@pytest.fixture
def list_use_case(extension_token_repository, time_provider):
    return ListExtensionTokensUseCase(
        extension_token_repository=extension_token_repository,
        time_provider=time_provider,
    )


@pytest.fixture
def revoke_use_case(extension_token_repository, event_publisher, admin_event_repository, time_provider):
    return RevokeExtensionTokenUseCase(
        extension_token_repository=extension_token_repository,
        event_publisher=event_publisher,
        admin_event_repository=admin_event_repository,
        time_provider=time_provider,
    )


@pytest.fixture
def revoke_all_use_case(extension_token_repository, event_publisher, admin_event_repository, time_provider):
    return RevokeAllExtensionTokensUseCase(
        extension_token_repository=extension_token_repository,
        event_publisher=event_publisher,
        admin_event_repository=admin_event_repository,
        time_provider=time_provider,
    )


def _issue(repository, user_id, now=NOW, lifetime=TOKEN_LIFETIME, device_name="Chrome on macOS"):
    secret = ExtensionTokenSecret.generate()
    token = ExtensionToken.create(
        user_id=user_id,
        secret=secret,
        device_name=device_name,
        lifetime=lifetime,
        now=now,
    )
    repository.add(token)
    return secret, token


class TestValidate:
    def test_resolves_a_live_credential_to_its_owner(
        self, validate_use_case, extension_token_repository, registered_user
    ):
        secret, token = _issue(extension_token_repository, registered_user.user_id)

        result = validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))

        assert result.user_id == registered_user.user_id
        assert result.email == registered_user.email
        assert result.token_id == token.id

    def test_never_returns_roles(self, validate_use_case, extension_token_repository, registered_user):
        # The caller builds a principal with a fixed non-admin role instead.
        # Echoing the user's own roles would make an admin's extension token
        # return the names, logins and URLs of every secret on the instance
        # through /passwords/list, into a browser profile.
        secret, _ = _issue(extension_token_repository, registered_user.user_id)

        result = validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))

        assert not hasattr(result, "roles")

    def test_rejects_an_unknown_credential(self, validate_use_case, registered_user):
        with pytest.raises(ExtensionTokenNotFoundError):
            validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=ExtensionTokenSecret.generate().value))

    def test_rejects_a_value_too_short_to_have_been_issued(self, validate_use_case):
        # Never reaches a database lookup.
        with pytest.raises(ExtensionTokenNotFoundError):
            validate_use_case.execute(ValidateExtensionTokenCommand(raw_token="short"))

    def test_rejects_a_revoked_credential(self, validate_use_case, extension_token_repository, registered_user):
        secret, token = _issue(extension_token_repository, registered_user.user_id)
        extension_token_repository.revoke(token.id, NOW)

        with pytest.raises(ExtensionTokenRevokedError):
            validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))

    def test_rejects_an_expired_credential(
        self, validate_use_case, extension_token_repository, time_provider, registered_user
    ):
        secret, _ = _issue(extension_token_repository, registered_user.user_id)

        time_provider.set_current_time(NOW + TOKEN_LIFETIME + timedelta(seconds=1))

        with pytest.raises(ExtensionTokenExpiredError):
            validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))

    def test_every_failure_carries_the_same_message(
        self, validate_use_case, extension_token_repository, registered_user
    ):
        # A token holder must not be able to tell revoked from expired from
        # never-existed; the distinct types exist only so the server can log
        # which one fired.
        secret, token = _issue(extension_token_repository, registered_user.user_id)
        extension_token_repository.revoke(token.id, NOW)

        with pytest.raises(ExtensionTokenRevokedError) as revoked:
            validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))
        with pytest.raises(ExtensionTokenNotFoundError) as missing:
            validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=ExtensionTokenSecret.generate().value))

        assert str(revoked.value) == str(missing.value)

    def test_honours_the_account_wide_session_cutoff(
        self, validate_use_case, extension_token_repository, user_repository, registered_user
    ):
        # The same cutoff a password change sets. Without this, "change my
        # password to log everything out" would leave every paired extension
        # alive.
        secret, _ = _issue(extension_token_repository, registered_user.user_id, now=NOW - timedelta(days=1))
        stored_user = user_repository.get_by_id(registered_user.user_id)
        stored_user.session_invalid_before = NOW

        with pytest.raises(ExtensionTokenRevokedError):
            validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))

    def test_a_credential_issued_after_the_cutoff_still_works(
        self, validate_use_case, extension_token_repository, user_repository, registered_user
    ):
        secret, _ = _issue(extension_token_repository, registered_user.user_id, now=NOW)
        stored_user = user_repository.get_by_id(registered_user.user_id)
        stored_user.session_invalid_before = NOW - timedelta(days=1)

        result = validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))

        assert result.user_id == registered_user.user_id

    def test_records_usage(self, validate_use_case, extension_token_repository, registered_user):
        secret, token = _issue(extension_token_repository, registered_user.user_id)

        validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))

        assert extension_token_repository.tokens[token.id].last_used_at == NOW

    def test_a_storage_failure_while_recording_usage_does_not_break_auth(
        self, validate_use_case, extension_token_repository, registered_user
    ):
        # Telemetry for a UI label must never be able to lock someone out.
        secret, _ = _issue(extension_token_repository, registered_user.user_id)
        extension_token_repository.raise_on_touch = True

        result = validate_use_case.execute(ValidateExtensionTokenCommand(raw_token=secret.value))

        assert result.user_id == registered_user.user_id


class TestListDevices:
    def test_lists_revoked_and_expired_devices_too(
        self, list_use_case, extension_token_repository, time_provider, user
    ):
        time_provider.set_current_time(NOW)
        _, live = _issue(extension_token_repository, user.user_id, device_name="Live")
        _, revoked = _issue(extension_token_repository, user.user_id, device_name="Revoked")
        extension_token_repository.revoke(revoked.id, NOW)

        result = list_use_case.execute(ListExtensionTokensCommand(requesting_user=user))

        # A user checking "did I actually disconnect that laptop" needs to see
        # the answer, not an empty row.
        by_name = {token.device_name: token for token in result.tokens}
        assert by_name["Live"].is_active is True
        assert by_name["Revoked"].is_active is False

    def test_does_not_list_another_users_devices(self, list_use_case, extension_token_repository, user):
        _issue(extension_token_repository, uuid4())

        result = list_use_case.execute(ListExtensionTokensCommand(requesting_user=user))

        assert result.tokens == []


class TestRevoke:
    def test_disconnects_one_device(self, revoke_use_case, extension_token_repository, time_provider, user):
        time_provider.set_current_time(NOW)
        _, token = _issue(extension_token_repository, user.user_id)

        revoke_use_case.execute(RevokeExtensionTokenCommand(token_id=token.id, requesting_user=user))

        assert extension_token_repository.tokens[token.id].revoked_at == NOW

    def test_someone_elses_device_is_reported_as_missing(
        self, revoke_use_case, extension_token_repository, time_provider, user
    ):
        # Not "forbidden": this route must not become a way to discover which
        # token ids exist on the instance.
        time_provider.set_current_time(NOW)
        _, other = _issue(extension_token_repository, uuid4())

        with pytest.raises(ExtensionTokenNotFoundError):
            revoke_use_case.execute(RevokeExtensionTokenCommand(token_id=other.id, requesting_user=user))
        assert extension_token_repository.tokens[other.id].revoked_at is None

    def test_revoking_twice_is_harmless_and_records_once(
        self, revoke_use_case, extension_token_repository, admin_event_repository, time_provider, user
    ):
        time_provider.set_current_time(NOW)
        _, token = _issue(extension_token_repository, user.user_id)
        command = RevokeExtensionTokenCommand(token_id=token.id, requesting_user=user)

        revoke_use_case.execute(command)
        revoke_use_case.execute(command)

        revocation_events = [
            event for event in admin_event_repository.events if event["event_type"] == "ExtensionTokenRevokedEvent"
        ]
        # A second audit entry would be misleading: nothing changed.
        assert len(revocation_events) == 1

    def test_revoke_all_disconnects_every_live_device(
        self, revoke_all_use_case, extension_token_repository, time_provider, user
    ):
        time_provider.set_current_time(NOW)
        _issue(extension_token_repository, user.user_id)
        _issue(extension_token_repository, user.user_id)
        _, other = _issue(extension_token_repository, uuid4())

        revoked = revoke_all_use_case.execute(RevokeAllExtensionTokensCommand(requesting_user=user))

        assert revoked == 2
        assert extension_token_repository.tokens[other.id].revoked_at is None

    def test_revoke_all_records_nothing_when_there_was_nothing_to_revoke(
        self, revoke_all_use_case, admin_event_repository, time_provider, user
    ):
        time_provider.set_current_time(NOW)

        assert revoke_all_use_case.execute(RevokeAllExtensionTokensCommand(requesting_user=user)) == 0
        assert admin_event_repository.events == []
