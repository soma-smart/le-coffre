from uuid import UUID

import pytest

from identity_access_management_context.domain.entities import SSOCredentialRecord, User
from identity_access_management_context.domain.value_objects import SSOCredential
from shared_kernel.domain.exceptions import AuthenticationError, OrphanedCredentialError, UnknownCredentialError

USER_ID = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e6")
PROVIDER = "google"
SUBJECT = "google_123456"


@pytest.fixture
def credential_record(sso_credential_record_repository) -> SSOCredentialRecord:
    credential_record = SSOCredentialRecord(principal_id=USER_ID, provider=PROVIDER, subject=SUBJECT)
    sso_credential_record_repository.create(credential_record)
    return credential_record


@pytest.fixture
def user(user_repository, credential_record) -> User:
    user = User(id=USER_ID, username="john", email="john@example.com", name="John Doe")
    user_repository.save(user)
    return user


def test_given_a_linked_subject_when_authenticating_then_its_user_is_returned(sso_authenticator, user):
    assert sso_authenticator.authenticate(SSOCredential(PROVIDER, SUBJECT)) == user


def test_given_an_unknown_subject_when_authenticating_then_it_is_refused(sso_authenticator, user):
    with pytest.raises(UnknownCredentialError):
        sso_authenticator.authenticate(SSOCredential(PROVIDER, "someone_else"))


def test_given_the_subject_from_another_provider_when_authenticating_then_it_is_refused(sso_authenticator, user):
    with pytest.raises(UnknownCredentialError):
        sso_authenticator.authenticate(SSOCredential("okta", SUBJECT))


def test_given_a_credential_whose_user_is_gone_when_authenticating_then_it_is_refused(
    sso_authenticator, credential_record
):
    with pytest.raises(OrphanedCredentialError):
        sso_authenticator.authenticate(SSOCredential(PROVIDER, SUBJECT))


def test_when_a_subject_is_refused_then_it_is_an_authentication_error(sso_authenticator):
    with pytest.raises(AuthenticationError):
        sso_authenticator.authenticate(SSOCredential(PROVIDER, SUBJECT))
