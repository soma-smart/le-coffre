from uuid import UUID

import pytest

from identity_access_management_context.domain.entities import PasswordCredentialRecord, User
from identity_access_management_context.domain.exceptions import (
    OrphanedPasswordCredentialError,
    UnknownPasswordEmailError,
    WrongPasswordError,
)
from identity_access_management_context.domain.value_objects import PasswordCredential
from shared_kernel.domain.exceptions import AuthenticationError

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


def test_given_an_unknown_email_when_authenticating_then_it_is_refused(password_authenticator, user):
    with pytest.raises(UnknownPasswordEmailError):
        password_authenticator.authenticate(PasswordCredential("nobody@lecoffre.com", PASSWORD))


def test_given_a_wrong_password_when_authenticating_then_it_is_refused(password_authenticator, user):
    with pytest.raises(WrongPasswordError):
        password_authenticator.authenticate(PasswordCredential(EMAIL, "wrong"))


def test_given_a_credential_whose_user_is_gone_when_authenticating_then_it_is_refused(
    password_authenticator, credential_record
):
    with pytest.raises(OrphanedPasswordCredentialError):
        password_authenticator.authenticate(PasswordCredential(EMAIL, PASSWORD))


def test_when_a_password_is_refused_then_it_is_an_authentication_error(password_authenticator):
    with pytest.raises(AuthenticationError):
        password_authenticator.authenticate(PasswordCredential(EMAIL, PASSWORD))


def test_when_reading_a_password_authentication_then_the_password_is_not_shown():
    assert PASSWORD not in repr(PasswordCredential(EMAIL, PASSWORD))
