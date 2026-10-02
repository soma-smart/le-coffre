from uuid import UUID, uuid4

import pytest

from identity_access_management_context.domain.entities import PasswordCredentialRecord, ServiceAccount, User
from identity_access_management_context.domain.value_objects import PasswordCredential
from shared_kernel.domain.exceptions import (
    AuthenticationError,
    OrphanedCredentialError,
    RejectedCredentialError,
    UnknownCredentialError,
)

USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
EMAIL = "admin@lecoffre.com"
PASSWORD = "secure123!"


@pytest.fixture
def credential_record(password_credential_record_repository, password_hashing_gateway) -> PasswordCredentialRecord:
    credential_record = PasswordCredentialRecord(
        principal_id=USER_ID, email=EMAIL, password_hash=password_hashing_gateway.hash(PASSWORD)
    )
    password_credential_record_repository.save(credential_record)
    return credential_record


@pytest.fixture
def user(user_repository, credential_record) -> User:
    user = User(id=USER_ID, username="admin", email=EMAIL, name="Admin User")
    user_repository.save(user)
    return user


def test_given_the_right_password_when_authenticating_then_its_user_is_returned(password_authenticator, user):
    assert password_authenticator.authenticate(PasswordCredential(EMAIL, PASSWORD)) == user


def test_given_a_password_held_by_another_kind_of_principal_when_authenticating_then_that_principal_is_returned(
    password_authenticator, password_credential_record_repository, password_hashing_gateway, service_account_repository
):
    account = ServiceAccount.create(group_id=uuid4(), name="nightly-backup")
    service_account_repository.create([account])
    password_credential_record_repository.save(
        PasswordCredentialRecord(
            principal_id=account.id, email="robot@lecoffre.com", password_hash=password_hashing_gateway.hash(PASSWORD)
        )
    )

    assert password_authenticator.authenticate(PasswordCredential("robot@lecoffre.com", PASSWORD)) == account


def test_given_an_unknown_email_when_authenticating_then_it_is_refused(password_authenticator, user):
    with pytest.raises(UnknownCredentialError):
        password_authenticator.authenticate(PasswordCredential("nobody@lecoffre.com", PASSWORD))


def test_given_a_wrong_password_when_authenticating_then_it_is_refused(password_authenticator, user):
    with pytest.raises(RejectedCredentialError):
        password_authenticator.authenticate(PasswordCredential(EMAIL, "wrong"))


def test_given_a_credential_whose_user_is_gone_when_authenticating_then_it_is_refused(
    password_authenticator, credential_record
):
    with pytest.raises(OrphanedCredentialError):
        password_authenticator.authenticate(PasswordCredential(EMAIL, PASSWORD))


def test_when_a_password_is_refused_then_it_is_an_authentication_error(password_authenticator):
    with pytest.raises(AuthenticationError):
        password_authenticator.authenticate(PasswordCredential(EMAIL, PASSWORD))


def test_when_reading_a_password_authentication_then_the_password_is_not_shown():
    assert PASSWORD not in repr(PasswordCredential(EMAIL, PASSWORD))
