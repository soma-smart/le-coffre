from uuid import uuid4

import pytest

from identity_access_management_context.application.services.authentication import (
    TokenAuthenticator,
)
from identity_access_management_context.domain.entities import ServiceAccount, TokenCredentialRecord
from identity_access_management_context.domain.value_objects import TokenCredential
from shared_kernel.domain.exceptions import AuthenticationError, UnknownCredentialError

from ..fakes import FakeServiceAccountRepository, FakeTokenCredentialRecordRepository


@pytest.fixture
def authenticator(principal_repository, token_credential_record_repository):
    return TokenAuthenticator(
        principal_repository=principal_repository,
        token_credential_record_repository=token_credential_record_repository,
    )


@pytest.fixture
def issue(
    service_account_repository: FakeServiceAccountRepository,
    token_credential_record_repository: FakeTokenCredentialRecordRepository,
):
    def _issue() -> tuple[ServiceAccount, TokenCredential]:
        token = TokenCredential.generate()
        account = ServiceAccount.create(group_id=uuid4(), name="nightly-backup")
        service_account_repository.create([account])
        token_credential_record_repository.create(
            [TokenCredentialRecord(principal_id=account.id, token_hash=token.hash)]
        )
        return account, token

    return _issue


def test_given_an_active_account_when_authenticating_with_its_token_then_the_account_is_returned(authenticator, issue):
    account, token = issue()

    assert authenticator.authenticate(TokenCredential(token.value)) == account


def test_given_an_account_with_two_tokens_when_authenticating_with_either_then_the_account_is_returned(
    authenticator, issue, token_credential_record_repository
):
    account, first = issue()
    second = TokenCredential.generate()
    token_credential_record_repository.create([TokenCredentialRecord(principal_id=account.id, token_hash=second.hash)])

    assert authenticator.authenticate(first) == account
    assert authenticator.authenticate(second) == account


def test_given_no_account_holds_the_token_when_authenticating_then_it_is_refused(authenticator):
    with pytest.raises(UnknownCredentialError):
        authenticator.authenticate(TokenCredential.generate())


def test_given_a_rotated_token_when_authenticating_with_the_old_one_then_it_is_refused(
    authenticator, issue, token_credential_record_repository
):
    account, old_token = issue()
    token_credential_record_repository.replace(
        [TokenCredentialRecord(principal_id=account.id, token_hash=TokenCredential.generate().hash)]
    )

    with pytest.raises(UnknownCredentialError):
        authenticator.authenticate(old_token)


def test_given_an_account_whose_token_records_were_deleted_when_authenticating_then_it_is_refused(
    authenticator, issue, token_credential_record_repository
):
    """Revoking an account deletes its token records: that alone shuts it out."""
    account, token = issue()
    token_credential_record_repository.delete_by_principal_ids([account.id])

    with pytest.raises(UnknownCredentialError):
        authenticator.authenticate(token)


def test_given_a_refused_token_when_reading_the_error_then_it_does_not_echo_the_token(authenticator):
    token = TokenCredential.generate()

    with pytest.raises(UnknownCredentialError) as error:
        authenticator.authenticate(token)

    assert token.value not in str(error.value)
    assert token.hash not in str(error.value)


def test_when_a_token_is_refused_then_it_is_an_authentication_error(authenticator):
    with pytest.raises(AuthenticationError):
        authenticator.authenticate(TokenCredential.generate())


def test_when_parsing_a_malformed_token_then_it_fails_like_an_unknown_token():
    """A malformed value fails before any lookup: no record could ever hold it."""
    with pytest.raises(UnknownCredentialError):
        TokenCredential("too-short")
