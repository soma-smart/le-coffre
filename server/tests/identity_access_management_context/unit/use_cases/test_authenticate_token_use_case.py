from datetime import timedelta
from uuid import uuid4

import pytest

from identity_access_management_context.application.commands import AuthenticateTokenCommand
from identity_access_management_context.application.services.authentication import TokenAuthenticator
from identity_access_management_context.application.use_cases import AuthenticateTokenUseCase
from identity_access_management_context.domain.entities import ServiceAccount, User
from identity_access_management_context.domain.exceptions import TokenAuthenticationError
from shared_kernel.domain.exceptions import CredentialAuthenticationError

COARSENING = timedelta(minutes=5)


@pytest.fixture
def use_case(
    principal_repository, token_credential_record_repository, event_publisher, admin_event_repository, time_provider
):
    return AuthenticateTokenUseCase(
        TokenAuthenticator(
            principal_repository=principal_repository,
            token_credential_record_repository=token_credential_record_repository,
            time_provider=time_provider,
        ),
        token_credential_record_repository,
        event_publisher,
        admin_event_repository,
        time_provider,
        int(COARSENING.total_seconds()),
    )


@pytest.fixture
def user(user_repository):
    user = User(id=uuid4(), username="alice", email="alice@example.com", name="Alice", roles=["admin"])
    user_repository.save(user)
    return user


def test_given_a_user_token_when_authenticating_then_the_user_and_the_credential_are_resolved(
    use_case, user, token_credential_record_repository, time_provider
):
    token = token_credential_record_repository.issue(user.id, time_provider.get_current_time())
    (record,) = token_credential_record_repository.list_by_principal_id(user.id)

    response = use_case.execute(AuthenticateTokenCommand(token=token.value))

    assert response.principal_id == user.id
    assert response.principal_kind == "user"
    assert response.roles == ["admin"]
    assert response.credential_id == record.id
    assert response.read_only is True


def test_given_a_service_account_token_when_authenticating_then_it_has_no_roles(
    use_case, service_account_repository, token_credential_record_repository, time_provider
):
    account = ServiceAccount.create(group_id=uuid4(), name="nightly-backup")
    service_account_repository.create([account])
    token = token_credential_record_repository.issue(account.id, time_provider.get_current_time(), read_only=False)

    response = use_case.execute(AuthenticateTokenCommand(token=token.value))

    assert response.principal_kind == "service_account"
    assert response.roles == []
    assert response.read_only is False


def test_given_a_token_when_authenticating_then_its_use_is_recorded(
    use_case, user, token_credential_record_repository, time_provider
):
    issued_at = time_provider.get_current_time()
    token = token_credential_record_repository.issue(user.id, issued_at)
    time_provider.set_current_time(issued_at + COARSENING)

    use_case.execute(AuthenticateTokenCommand(token=token.value))

    (record,) = token_credential_record_repository.list_by_principal_id(user.id)
    assert record.last_used_at == issued_at + COARSENING


def test_given_recording_the_use_fails_when_authenticating_then_the_caller_is_still_authenticated(
    use_case, user, token_credential_record_repository, time_provider, monkeypatch
):
    token = token_credential_record_repository.issue(user.id, time_provider.get_current_time())

    def fail(*_args):
        raise RuntimeError("storage hiccup")

    monkeypatch.setattr(token_credential_record_repository, "touch_last_used", fail)

    assert use_case.execute(AuthenticateTokenCommand(token=token.value)).principal_id == user.id


@pytest.mark.parametrize("value", ["short", "x" * 43])
def test_given_a_malformed_or_unknown_token_when_authenticating_then_it_is_refused(use_case, value):
    with pytest.raises(CredentialAuthenticationError):
        use_case.execute(AuthenticateTokenCommand(token=value))


@pytest.mark.parametrize(
    ("value", "reason"),
    [(None, "missing_token"), ("short", "malformed_token"), ("x" * 43, "unknown_token")],
)
def test_given_an_unusable_value_when_authenticating_then_the_reason_is_told(use_case, value, reason):
    with pytest.raises(TokenAuthenticationError) as error:
        use_case.execute(AuthenticateTokenCommand(token=value))

    assert error.value.reason == reason


def test_given_an_expired_token_when_authenticating_then_it_is_refused_as_unusable(
    use_case, user, token_credential_record_repository, time_provider
):
    now = time_provider.get_current_time()
    token = token_credential_record_repository.issue(user.id, now, expires_at=now)

    with pytest.raises(TokenAuthenticationError) as error:
        use_case.execute(AuthenticateTokenCommand(token=token.value))

    assert error.value.reason == "unusable_token"


def test_given_a_user_token_when_a_service_account_is_required_then_it_is_refused(
    use_case, user, token_credential_record_repository, time_provider
):
    token = token_credential_record_repository.issue(user.id, time_provider.get_current_time())

    with pytest.raises(TokenAuthenticationError) as error:
        use_case.execute(AuthenticateTokenCommand(token=token.value, required_kind="service_account"))

    assert error.value.reason == "principal_not_allowed"
    assert error.value.principal_id == user.id


def test_given_the_token_of_a_revoked_service_account_when_authenticating_then_it_is_refused(
    use_case, service_account_repository, token_credential_record_repository, time_provider
):
    """Revoking deletes the tokens: this guards a revocation that failed halfway."""
    now = time_provider.get_current_time()
    account = ServiceAccount.create(group_id=uuid4(), name="nightly-backup")
    service_account_repository.create([account])
    token = token_credential_record_repository.issue(account.id, now, read_only=False)
    service_account_repository.revoke([account.id], now)

    with pytest.raises(TokenAuthenticationError) as error:
        use_case.execute(AuthenticateTokenCommand(token=token.value))

    assert error.value.reason == "inactive_principal"


def test_given_a_refused_token_when_authenticating_then_the_failure_is_recorded_without_the_token(
    use_case, user, token_credential_record_repository, admin_event_repository, time_provider
):
    token = token_credential_record_repository.issue(user.id, time_provider.get_current_time())

    with pytest.raises(TokenAuthenticationError):
        use_case.execute(
            AuthenticateTokenCommand(token=token.value, client_ip="203.0.113.7", required_kind="service_account")
        )

    (entry,) = admin_event_repository.events
    assert entry["event_type"] == "TokenAuthenticationFailedEvent"
    assert entry["actor_principal_id"] is None
    assert entry["event_data"] == {
        "reason": "principal_not_allowed",
        "client_ip": "203.0.113.7",
        "principal_id": str(user.id),
    }


def test_given_an_accepted_token_when_authenticating_then_nothing_is_recorded(
    use_case, user, token_credential_record_repository, admin_event_repository, time_provider
):
    token = token_credential_record_repository.issue(user.id, time_provider.get_current_time())

    use_case.execute(AuthenticateTokenCommand(token=token.value))

    assert admin_event_repository.events == []
