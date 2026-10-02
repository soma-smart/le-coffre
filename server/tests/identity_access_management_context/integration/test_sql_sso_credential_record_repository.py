from datetime import datetime
from uuid import uuid4

import pytest

from identity_access_management_context.domain.entities import SSOCredentialRecord
from identity_access_management_context.domain.exceptions import (
    SSOCredentialAlreadyExistsException,
)


def _credential_record(**overrides) -> SSOCredentialRecord:
    fields = {"principal_id": uuid4(), "provider": "google", "subject": "sso123"} | overrides
    return SSOCredentialRecord(**fields)


def test_create_sso_credential_and_list_by_principal_id(sql_sso_credential_record_repository):
    credential_record = _credential_record()
    sql_sso_credential_record_repository.create(credential_record)
    (retrieved,) = sql_sso_credential_record_repository.list_by_principal_id(credential_record.principal_id)
    assert retrieved.provider == credential_record.provider
    assert retrieved.subject == credential_record.subject


def test_sso_credential_already_exists(sql_sso_credential_record_repository):
    credential_record = _credential_record()
    sql_sso_credential_record_repository.create(credential_record)
    with pytest.raises(SSOCredentialAlreadyExistsException):
        sql_sso_credential_record_repository.create(_credential_record())


def test_get_nonexistent_sso_subject(sql_sso_credential_record_repository):
    assert sql_sso_credential_record_repository.get_by_subject("google", str(uuid4())) is None


def test_get_by_subject(sql_sso_credential_record_repository):
    credential_record = _credential_record()
    sql_sso_credential_record_repository.create(credential_record)
    retrieved = sql_sso_credential_record_repository.get_by_subject("google", "sso123")
    assert retrieved is not None
    assert retrieved.principal_id == credential_record.principal_id


def test_same_subject_from_another_provider_is_another_credential(sql_sso_credential_record_repository):
    sql_sso_credential_record_repository.create(_credential_record())
    other = _credential_record(provider="okta")
    sql_sso_credential_record_repository.create(other)
    found = sql_sso_credential_record_repository.get_by_subject("okta", "sso123")
    assert found is not None
    assert found.principal_id == other.principal_id


def test_update_last_login(sql_sso_credential_record_repository):
    sql_sso_credential_record_repository.create(_credential_record())
    last_login = datetime(2026, 1, 2, 3, 4, 5)
    sql_sso_credential_record_repository.update_last_login("google", "sso123", last_login)
    found = sql_sso_credential_record_repository.get_by_subject("google", "sso123")
    assert found is not None
    assert found.last_login == last_login


def test_given_two_subjects_of_one_principal_when_listing_then_both_are_returned(sql_sso_credential_record_repository):
    principal_id = uuid4()
    google = _credential_record(principal_id=principal_id, provider="google", subject="g-1")
    okta = _credential_record(principal_id=principal_id, provider="okta", subject="o-1")
    sql_sso_credential_record_repository.create(google)
    sql_sso_credential_record_repository.create(okta)

    listed = sql_sso_credential_record_repository.list_by_principal_id(principal_id)

    assert sorted((c.provider, c.subject) for c in listed) == [("google", "g-1"), ("okta", "o-1")]
