from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from identity_access_management_context.domain.entities import PasswordCredentialRecord


def test_save_password_credential_and_list_by_principal_id(sql_password_credential_record_repository):
    credential_record = PasswordCredentialRecord(
        principal_id=uuid4(), email="test@example.com", password_hash=b"hashedpassword123"
    )
    sql_password_credential_record_repository.save(credential_record)
    assert sql_password_credential_record_repository.list_by_principal_id(credential_record.principal_id) == [
        credential_record
    ]


def test_given_two_passwords_of_one_principal_when_listing_then_both_are_returned(
    sql_password_credential_record_repository,
):
    principal_id = uuid4()
    work = PasswordCredentialRecord(principal_id=principal_id, email="work@example.com", password_hash=b"work-hash")
    home = PasswordCredentialRecord(principal_id=principal_id, email="home@example.com", password_hash=b"home-hash")
    sql_password_credential_record_repository.save(work)
    sql_password_credential_record_repository.save(home)

    listed = sql_password_credential_record_repository.list_by_principal_id(principal_id)

    assert sorted(listed, key=lambda c: c.email) == [home, work]


def test_get_password_credential_by_email(sql_password_credential_record_repository):
    credential_record = PasswordCredentialRecord(
        principal_id=uuid4(), email="test@example.com", password_hash=b"hashedpassword123"
    )
    sql_password_credential_record_repository.save(credential_record)
    assert sql_password_credential_record_repository.get_by_email(credential_record.email) == credential_record


def test_list_password_credentials_of_a_principal_without_any(sql_password_credential_record_repository):
    assert sql_password_credential_record_repository.list_by_principal_id(uuid4()) == []


def test_update_password_hash(sql_password_credential_record_repository):
    credential_record = PasswordCredentialRecord(
        principal_id=UUID("12345678-1234-5678-1234-567812345678"),
        email="toto@toto.com",
        password_hash=b"hashedpassword123",
    )
    sql_password_credential_record_repository.save(credential_record)

    new_password = b"newhashedpassword123"
    sql_password_credential_record_repository.update_password_hash(credential_record.email, new_password)

    (updated,) = sql_password_credential_record_repository.list_by_principal_id(credential_record.principal_id)
    assert updated.email == credential_record.email
    assert updated.password_hash == new_password


def test_given_two_passwords_when_updating_one_by_email_then_the_other_is_untouched(
    sql_password_credential_record_repository,
):
    principal_id = uuid4()
    sql_password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=principal_id, email="work@example.com", password_hash=b"work-hash")
    )
    sql_password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=principal_id, email="home@example.com", password_hash=b"home-hash")
    )

    sql_password_credential_record_repository.update_password_hash("home@example.com", b"new-hash")

    hashes = {
        c.email: c.password_hash for c in sql_password_credential_record_repository.list_by_principal_id(principal_id)
    }
    assert hashes == {"work@example.com": b"work-hash", "home@example.com": b"new-hash"}


def test_update_missing_credential_does_nothing(sql_password_credential_record_repository):
    sql_password_credential_record_repository.update_password_hash("nobody@example.com", b"new_password_hashed")


def test_given_an_email_already_held_when_saving_another_password_with_it_then_it_is_refused(
    sql_password_credential_record_repository,
):
    """The email identifies the record a password is checked against, so it cannot be shared."""
    email = "taken@example.com"
    sql_password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=uuid4(), email=email, password_hash=b"first-hash")
    )

    with pytest.raises(IntegrityError):
        sql_password_credential_record_repository.save(
            PasswordCredentialRecord(principal_id=uuid4(), email=email, password_hash=b"second-hash")
        )
