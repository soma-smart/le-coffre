from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from identity_access_management_context.domain.entities import ServiceAccountTokenCredentialRecord
from identity_access_management_context.domain.value_objects import ServiceAccountToken


def _credential_record(principal_id=None, token=None) -> ServiceAccountTokenCredentialRecord:
    token = token or ServiceAccountToken.generate()
    return ServiceAccountTokenCredentialRecord(principal_id=principal_id or uuid4(), token_hash=token.hash)


def test_given_a_credential_when_looking_up_its_token_hash_then_it_is_found(
    sql_service_account_token_credential_record_repository, session
):
    credential_record = _credential_record()
    sql_service_account_token_credential_record_repository.create([credential_record, _credential_record()])
    session.expunge_all()

    assert (
        sql_service_account_token_credential_record_repository.get_by_token_hash(credential_record.token_hash)
        == credential_record
    )


def test_given_no_matching_hash_when_looking_up_then_nothing_is_found(
    sql_service_account_token_credential_record_repository,
):
    sql_service_account_token_credential_record_repository.create([_credential_record()])

    assert (
        sql_service_account_token_credential_record_repository.get_by_token_hash(ServiceAccountToken.generate().hash)
        is None
    )


def test_given_a_credential_when_replacing_it_then_only_the_new_hash_is_found(
    sql_service_account_token_credential_record_repository, session
):
    old = _credential_record()
    sql_service_account_token_credential_record_repository.create([old])
    new = _credential_record(principal_id=old.principal_id)

    sql_service_account_token_credential_record_repository.replace([new])
    session.expunge_all()

    assert sql_service_account_token_credential_record_repository.get_by_token_hash(new.token_hash) == new
    assert sql_service_account_token_credential_record_repository.get_by_token_hash(old.token_hash) is None


def test_given_a_duplicate_token_hash_when_creating_then_the_unique_index_refuses_it(
    sql_service_account_token_credential_record_repository,
):
    token = ServiceAccountToken.generate()
    sql_service_account_token_credential_record_repository.create([_credential_record(token=token)])

    with pytest.raises(IntegrityError):
        sql_service_account_token_credential_record_repository.create([_credential_record(token=token)])
