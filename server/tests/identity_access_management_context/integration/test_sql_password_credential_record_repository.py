from uuid import UUID, uuid4

from identity_access_management_context.domain.entities import PasswordCredentialRecord


def test_save_password_credential_and_get_by_principal_id(sql_password_credential_record_repository):
    credential_record = PasswordCredentialRecord(
        principal_id=uuid4(), email="test@example.com", password_hash=b"hashedpassword123"
    )
    sql_password_credential_record_repository.save(credential_record)
    assert (
        sql_password_credential_record_repository.get_by_principal_id(credential_record.principal_id)
        == credential_record
    )


def test_get_password_credential_by_email(sql_password_credential_record_repository):
    credential_record = PasswordCredentialRecord(
        principal_id=uuid4(), email="test@example.com", password_hash=b"hashedpassword123"
    )
    sql_password_credential_record_repository.save(credential_record)
    assert sql_password_credential_record_repository.get_by_email(credential_record.email) == credential_record


def test_get_nonexistent_password_credential_by_principal_id(sql_password_credential_record_repository):
    assert sql_password_credential_record_repository.get_by_principal_id(uuid4()) is None


def test_update_password_hash(sql_password_credential_record_repository):
    credential_record = PasswordCredentialRecord(
        principal_id=UUID("12345678-1234-5678-1234-567812345678"),
        email="toto@toto.com",
        password_hash=b"hashedpassword123",
    )
    sql_password_credential_record_repository.save(credential_record)

    new_password = b"newhashedpassword123"
    sql_password_credential_record_repository.update_password_hash(credential_record.principal_id, new_password)

    updated = sql_password_credential_record_repository.get_by_principal_id(credential_record.principal_id)
    assert updated is not None
    assert updated.email == credential_record.email
    assert updated.password_hash == new_password


def test_update_missing_credential_does_nothing(sql_password_credential_record_repository):
    sql_password_credential_record_repository.update_password_hash(
        UUID("12345678-1234-5678-1234-567812345678"), b"new_password_hashed"
    )


def test_delete_by_principal_id_removes_the_credential(sql_password_credential_record_repository):
    credential_record = PasswordCredentialRecord(
        principal_id=uuid4(), email="leaver@example.com", password_hash=b"hashedpassword123"
    )
    sql_password_credential_record_repository.save(credential_record)

    sql_password_credential_record_repository.delete_by_principal_id(credential_record.principal_id)

    assert sql_password_credential_record_repository.get_by_principal_id(credential_record.principal_id) is None
    assert sql_password_credential_record_repository.get_by_email(credential_record.email) is None


def test_delete_by_principal_id_on_a_missing_row_does_nothing(sql_password_credential_record_repository):
    sql_password_credential_record_repository.delete_by_principal_id(uuid4())


def test_delete_frees_the_email_for_a_new_account(sql_password_credential_record_repository):
    """get_by_email takes the first match, so a leftover row would shadow the new one."""
    email = "reused@example.com"
    old = PasswordCredentialRecord(principal_id=uuid4(), email=email, password_hash=b"old-hash")
    sql_password_credential_record_repository.save(old)
    sql_password_credential_record_repository.delete_by_principal_id(old.principal_id)

    new = PasswordCredentialRecord(principal_id=uuid4(), email=email, password_hash=b"new-hash")
    sql_password_credential_record_repository.save(new)

    assert sql_password_credential_record_repository.get_by_email(email) == new
