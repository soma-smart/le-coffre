from datetime import timedelta
from uuid import uuid4

import pytest

from identity_access_management_context.application.commands import AuthenticateTokenCommand
from identity_access_management_context.application.services.authentication import TokenAuthenticator
from identity_access_management_context.application.use_cases import AuthenticateTokenUseCase
from identity_access_management_context.domain.entities import ServiceAccount, User
from shared_kernel.domain.exceptions import AuthenticationError

COARSENING = timedelta(minutes=5)


@pytest.fixture
def use_case(principal_repository, token_credential_record_repository, time_provider):
    return AuthenticateTokenUseCase(
        TokenAuthenticator(
            principal_repository=principal_repository,
            token_credential_record_repository=token_credential_record_repository,
            time_provider=time_provider,
        ),
        token_credential_record_repository,
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
    with pytest.raises(AuthenticationError):
        use_case.execute(AuthenticateTokenCommand(token=value))
