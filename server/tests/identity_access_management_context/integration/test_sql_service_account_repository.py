from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlmodel import Session

from identity_access_management_context.adapters.secondary.sql import (
    PrincipalKind,
    PrincipalTable,
    SqlServiceAccountRepository,
)
from identity_access_management_context.adapters.secondary.sql.model.service_account_model import (
    ServiceAccountPrincipalTable,
)
from identity_access_management_context.application.gateways import CannotRevokeServiceAccount
from identity_access_management_context.domain.entities import ServiceAccount

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)


def _account(group_id=None, name="nightly-backup"):
    return ServiceAccount.create(group_id=group_id or uuid4(), name=name)


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


def test_given_created_accounts_then_each_is_registered_as_a_service_account_principal(
    sql_service_account_repository, session
):
    accounts = [_account(name="one"), _account(name="two")]

    sql_service_account_repository.create(accounts)

    for account in accounts:
        principal = session.get(PrincipalTable, account.id)
        assert principal is not None
        assert principal.kind == PrincipalKind.SERVICE_ACCOUNT


def test_given_a_revocation_committed_by_another_session_when_reading_again_then_it_shows(
    sql_service_account_repository, session, database_engine
):
    """Sessions do not expire on commit, so a cached row must not hide another request's revocation.

    Rotation relies on this to notice a revocation that landed while it was writing the new token.
    """
    account = _account()
    sql_service_account_repository.create([account])
    (before,) = sql_service_account_repository.get_by_ids([account.id])
    assert before.is_active
    # Held, as anything else in the request might: the session then keeps the row cached.
    cached_row = session.get(ServiceAccountPrincipalTable, account.id)

    with Session(database_engine, expire_on_commit=False) as other_session:
        SqlServiceAccountRepository(other_session).revoke([account.id], NOW)

    (after,) = sql_service_account_repository.get_by_ids([account.id])
    assert not after.is_active
    assert cached_row.revoked_at is not None
