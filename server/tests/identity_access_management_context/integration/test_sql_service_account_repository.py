from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from identity_access_management_context.application.gateways import (
    CannotRevokeServiceAccount,
    CannotRotateServiceAccount,
)
from identity_access_management_context.domain.entities import ServiceAccount
from identity_access_management_context.domain.value_objects import ServiceAccountToken

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)


def _account(group_id=None, name="nightly-backup"):
    return ServiceAccount.create(group_id=group_id or uuid4(), name=name, token=ServiceAccountToken.generate())


def test_given_an_account_when_read_back_then_its_fields_round_trip(sql_service_account_repository, session):
    account = _account()
    sql_service_account_repository.create([account])
    session.expunge_all()

    (loaded,) = sql_service_account_repository.get_by_ids([account.id])

    assert loaded == account
    assert loaded.is_active


def test_given_a_revoked_account_when_read_back_then_its_timestamp_is_timezone_aware(
    sql_service_account_repository, session
):
    """A naive datetime reaching the domain would raise on any comparison with an aware `now`."""
    account = _account()
    sql_service_account_repository.create([account])
    sql_service_account_repository.revoke([account.id], NOW)
    session.expunge_all()

    (loaded,) = sql_service_account_repository.get_by_ids([account.id])

    assert loaded.revoked_at is not None
    assert loaded.revoked_at.tzinfo is not None
    assert loaded.revoked_at == NOW


def test_given_unknown_ids_when_getting_then_slots_come_back_empty_in_order(sql_service_account_repository):
    account = _account()
    sql_service_account_repository.create([account])
    missing = uuid4()

    result = sql_service_account_repository.get_by_ids([missing, account.id, missing])

    assert [r.id if r else None for r in result] == [None, account.id, None]


def test_given_accounts_in_several_groups_when_listing_then_only_the_groups_own_come_back(
    sql_service_account_repository,
):
    group_id = uuid4()
    mine = [_account(group_id, "a"), _account(group_id, "b")]
    sql_service_account_repository.create([*mine, _account(uuid4(), "elsewhere")])

    listed = list(sql_service_account_repository.list_for_groups((group_id,)))

    assert {a.id for a in listed} == {a.id for a in mine}


def test_given_a_revoked_account_when_listing_then_it_still_comes_back(sql_service_account_repository):
    group_id = uuid4()
    account = _account(group_id)
    sql_service_account_repository.create([account])
    sql_service_account_repository.revoke([account.id], NOW)

    (listed,) = list(sql_service_account_repository.list_for_groups((group_id,)))

    assert not listed.is_active


def test_given_an_active_account_when_rotating_then_the_hash_is_replaced(sql_service_account_repository, session):
    account = _account()
    sql_service_account_repository.create([account])
    new_token = ServiceAccountToken.generate()

    sql_service_account_repository.rotate([account.id], [new_token.hash])
    session.expunge_all()

    (loaded,) = sql_service_account_repository.get_by_ids([account.id])
    assert loaded.token_hash == new_token.hash
    assert loaded.token_hash != account.token_hash


def test_given_a_revoked_account_when_rotating_then_it_is_refused_and_the_hash_stands(
    sql_service_account_repository, session
):
    account = _account()
    sql_service_account_repository.create([account])
    sql_service_account_repository.revoke([account.id], NOW)
    original_hash = account.token_hash

    with pytest.raises(CannotRotateServiceAccount):
        sql_service_account_repository.rotate([account.id], [ServiceAccountToken.generate().hash])
    session.expunge_all()

    (loaded,) = sql_service_account_repository.get_by_ids([account.id])
    assert loaded.token_hash == original_hash


def test_given_a_batch_with_one_revoked_account_when_rotating_then_none_are_rotated(
    sql_service_account_repository, session
):
    """The batch is refused whole, so a caller never has to guess which half applied."""
    healthy, revoked = _account(name="a"), _account(name="b")
    sql_service_account_repository.create([healthy, revoked])
    sql_service_account_repository.revoke([revoked.id], NOW)

    with pytest.raises(CannotRotateServiceAccount):
        sql_service_account_repository.rotate(
            [healthy.id, revoked.id],
            [ServiceAccountToken.generate().hash, ServiceAccountToken.generate().hash],
        )
    session.expunge_all()

    (loaded,) = sql_service_account_repository.get_by_ids([healthy.id])
    assert loaded.token_hash == healthy.token_hash


def test_given_an_already_revoked_account_when_revoking_again_then_the_first_timestamp_stands(
    sql_service_account_repository, session
):
    account = _account()
    sql_service_account_repository.create([account])
    sql_service_account_repository.revoke([account.id], NOW)

    with pytest.raises(CannotRevokeServiceAccount):
        sql_service_account_repository.revoke([account.id], LATER)
    session.expunge_all()

    (loaded,) = sql_service_account_repository.get_by_ids([account.id])
    assert loaded.revoked_at == NOW


def test_given_a_duplicate_token_hash_when_creating_then_the_unique_index_refuses_it(
    sql_service_account_repository,
):
    token = ServiceAccountToken.generate()
    first = ServiceAccount.create(group_id=uuid4(), name="a", token=token)
    second = ServiceAccount.create(group_id=uuid4(), name="b", token=token)
    sql_service_account_repository.create([first])

    with pytest.raises(IntegrityError):
        sql_service_account_repository.create([second])
