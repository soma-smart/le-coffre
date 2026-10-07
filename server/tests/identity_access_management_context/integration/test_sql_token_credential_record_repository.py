from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from identity_access_management_context.adapters.secondary.sql import CredentialRecordTable
from identity_access_management_context.application.gateways import CannotRotateTokenCredentialError
from identity_access_management_context.domain.entities import TokenCredentialRecord
from identity_access_management_context.domain.value_objects import TokenCredential


def _credential_record(principal_id=None, token=None) -> TokenCredentialRecord:
    token = token or TokenCredential.generate()
    return TokenCredentialRecord(principal_id=principal_id or uuid4(), token_hash=token.hash)


def test_given_a_credential_when_looking_up_its_token_hash_then_it_is_found(
    sql_token_credential_record_repository, session
):
    credential_record = _credential_record()
    sql_token_credential_record_repository.create([credential_record, _credential_record()])
    session.expunge_all()

    assert sql_token_credential_record_repository.get_by_token_hash(credential_record.token_hash) == credential_record


def test_given_no_matching_hash_when_looking_up_then_nothing_is_found(
    sql_token_credential_record_repository,
):
    sql_token_credential_record_repository.create([_credential_record()])

    assert sql_token_credential_record_repository.get_by_token_hash(TokenCredential.generate().hash) is None


def test_given_a_credential_when_rotating_it_then_only_the_new_token_is_found(
    sql_token_credential_record_repository, session
):
    old = _credential_record()
    sql_token_credential_record_repository.create([old])

    (new_token,) = sql_token_credential_record_repository.rotate([old.token_hash])
    session.expunge_all()

    new_hash = TokenCredential(new_token).hash
    assert sql_token_credential_record_repository.get_by_token_hash(new_hash) == TokenCredentialRecord(
        principal_id=old.principal_id, token_hash=new_hash
    )
    assert sql_token_credential_record_repository.get_by_token_hash(old.token_hash) is None


def test_given_a_duplicate_token_hash_when_creating_then_the_unique_index_refuses_it(
    sql_token_credential_record_repository,
):
    token = TokenCredential.generate()
    sql_token_credential_record_repository.create([_credential_record(token=token)])

    with pytest.raises(IntegrityError):
        sql_token_credential_record_repository.create([_credential_record(token=token)])


def test_given_credentials_of_several_accounts_when_deleting_some_then_only_theirs_are_gone(
    sql_token_credential_record_repository, session
):
    deleted, kept = _credential_record(), _credential_record()
    sql_token_credential_record_repository.create([deleted, kept])

    sql_token_credential_record_repository.delete_by_principal_ids([deleted.principal_id])
    session.expunge_all()

    assert sql_token_credential_record_repository.get_by_token_hash(deleted.token_hash) is None
    assert sql_token_credential_record_repository.get_by_token_hash(kept.token_hash) == kept
    registry = select(CredentialRecordTable).where(CredentialRecordTable.principal_id == deleted.principal_id)
    assert session.exec(registry).all() == []


def test_given_two_tokens_of_one_account_when_looking_each_up_then_both_are_found(
    sql_token_credential_record_repository, session
):
    principal_id = uuid4()
    first, second = _credential_record(principal_id=principal_id), _credential_record(principal_id=principal_id)
    sql_token_credential_record_repository.create([first, second])
    session.expunge_all()

    assert sql_token_credential_record_repository.get_by_token_hash(first.token_hash) == first
    assert sql_token_credential_record_repository.get_by_token_hash(second.token_hash) == second


def test_given_two_tokens_of_one_account_when_rotating_both_then_each_gets_its_own_new_token(
    sql_token_credential_record_repository, session
):
    principal_id = uuid4()
    first, second = _credential_record(principal_id=principal_id), _credential_record(principal_id=principal_id)
    sql_token_credential_record_repository.create([first, second])

    new_tokens = sql_token_credential_record_repository.rotate([first.token_hash, second.token_hash])
    session.expunge_all()

    new_hashes = [TokenCredential(token).hash for token in new_tokens]
    assert len(set(new_hashes)) == 2
    for new_hash in new_hashes:
        assert sql_token_credential_record_repository.get_by_token_hash(new_hash).principal_id == principal_id
    for old in (first, second):
        assert sql_token_credential_record_repository.get_by_token_hash(old.token_hash) is None


def test_given_a_token_no_longer_stored_when_rotating_then_it_is_refused_and_nothing_is_written(
    sql_token_credential_record_repository, session
):
    """A revocation deletes the tokens: rotating them afterwards must not bring any back."""
    gone = _credential_record()

    with pytest.raises(CannotRotateTokenCredentialError):
        sql_token_credential_record_repository.rotate([gone.token_hash])
    session.expunge_all()

    assert session.exec(select(CredentialRecordTable)).all() == []


def test_given_a_batch_with_one_token_no_longer_stored_when_rotating_then_none_are_rotated(
    sql_token_credential_record_repository, session
):
    """The batch is refused whole, so a caller never has to guess which part applied."""
    held, gone = _credential_record(), _credential_record()
    sql_token_credential_record_repository.create([held])

    with pytest.raises(CannotRotateTokenCredentialError):
        sql_token_credential_record_repository.rotate([held.token_hash, gone.token_hash])
    session.expunge_all()

    assert sql_token_credential_record_repository.get_by_token_hash(held.token_hash) == held


def test_given_tokens_of_another_account_when_rotating_then_they_are_untouched(
    sql_token_credential_record_repository, session
):
    rotated, bystander = _credential_record(), _credential_record()
    sql_token_credential_record_repository.create([rotated, bystander])

    sql_token_credential_record_repository.rotate([rotated.token_hash])
    session.expunge_all()

    assert sql_token_credential_record_repository.get_by_token_hash(bystander.token_hash) == bystander
