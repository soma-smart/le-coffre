from datetime import UTC, datetime
from uuid import uuid4

import pytest

from identity_access_management_context.application.services.authentication import (
    ServiceAccountTokenAuthenticator,
)
from identity_access_management_context.domain.entities import ServiceAccount, ServiceAccountTokenCredentialRecord
from identity_access_management_context.domain.exceptions import ServiceAccountTokenAuthenticationError
from identity_access_management_context.domain.value_objects import ServiceAccountToken
from shared_kernel.domain.exceptions import AuthenticationError

from ..fakes import FakeServiceAccountRepository, FakeServiceAccountTokenCredentialRecordRepository

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def authenticator(service_account_token_credential_record_repository, service_account_repository):
    return ServiceAccountTokenAuthenticator(
        service_account_token_credential_record_repository, service_account_repository
    )


@pytest.fixture
def issue(
    service_account_repository: FakeServiceAccountRepository,
    service_account_token_credential_record_repository: FakeServiceAccountTokenCredentialRecordRepository,
):
    def _issue() -> tuple[ServiceAccount, ServiceAccountToken]:
        token = ServiceAccountToken.generate()
        account = ServiceAccount.create(group_id=uuid4(), name="nightly-backup")
        service_account_repository.create([account])
        service_account_token_credential_record_repository.create(
            [ServiceAccountTokenCredentialRecord(principal_id=account.id, token_hash=token.hash)]
        )
        return account, token

    return _issue


def test_given_an_active_account_when_authenticating_with_its_token_then_the_account_is_returned(authenticator, issue):
    account, token = issue()

    assert authenticator.authenticate(ServiceAccountToken(token.value)) == account


def test_given_no_account_holds_the_token_when_authenticating_then_it_is_refused(authenticator):
    with pytest.raises(ServiceAccountTokenAuthenticationError):
        authenticator.authenticate(ServiceAccountToken.generate())


def test_given_a_rotated_token_when_authenticating_with_the_old_one_then_it_is_refused(
    authenticator, issue, service_account_token_credential_record_repository
):
    account, old_token = issue()
    service_account_token_credential_record_repository.replace(
        [ServiceAccountTokenCredentialRecord(principal_id=account.id, token_hash=ServiceAccountToken.generate().hash)]
    )

    with pytest.raises(ServiceAccountTokenAuthenticationError):
        authenticator.authenticate(old_token)


def test_given_a_revoked_account_when_authenticating_then_it_is_refused(
    authenticator, issue, service_account_repository
):
    account, token = issue()
    service_account_repository.revoke([account.id], NOW)

    with pytest.raises(ServiceAccountTokenAuthenticationError):
        authenticator.authenticate(token)


def test_given_a_refused_token_when_reading_the_error_then_it_does_not_echo_the_token(authenticator):
    token = ServiceAccountToken.generate()

    with pytest.raises(ServiceAccountTokenAuthenticationError) as error:
        authenticator.authenticate(token)

    assert token.value not in str(error.value)
    assert token.hash not in str(error.value)


def test_when_a_token_is_refused_then_it_is_an_authentication_error(authenticator):
    with pytest.raises(AuthenticationError):
        authenticator.authenticate(ServiceAccountToken.generate())


def test_when_parsing_a_malformed_token_then_it_is_this_authenticator_s_error():
    """A malformed value fails before any lookup, but it is still a failed proof."""
    with pytest.raises(ServiceAccountTokenAuthenticationError):
        ServiceAccountToken("too-short")
