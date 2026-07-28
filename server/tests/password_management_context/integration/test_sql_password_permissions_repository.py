from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from password_management_context.adapters.secondary.sql import (
    SqlPasswordPermissionsRepository,
)
from password_management_context.domain.value_objects import (
    PasswordPermission,
)


@pytest.fixture
def sql_password_permissions_repository(session):
    return SqlPasswordPermissionsRepository(session)


def test_set_owner_creates_ownership(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    sql_password_permissions_repository.set_owner(user_id, password_id)

    # Then
    assert sql_password_permissions_repository.is_owner(user_id, password_id)


def test_set_owner_is_idempotent(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    sql_password_permissions_repository.set_owner(user_id, password_id)
    sql_password_permissions_repository.set_owner(user_id, password_id)

    # Then - no exception should be raised
    assert sql_password_permissions_repository.is_owner(user_id, password_id)


def test_is_owner_returns_true_for_owner(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.set_owner(user_id, password_id)

    # When
    result = sql_password_permissions_repository.is_owner(user_id, password_id)

    # Then
    assert result is True


def test_is_owner_returns_false_for_non_owner(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    result = sql_password_permissions_repository.is_owner(user_id, password_id)

    # Then
    assert result is False


def test_has_access_ignoring_expiry_returns_true_for_owner(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.set_owner(user_id, password_id)

    # When
    result = sql_password_permissions_repository.has_access_ignoring_expiry(
        user_id, password_id, PasswordPermission.READ
    )

    # Then
    assert result is True


def test_has_access_ignoring_expiry_returns_true_for_granted_permission(
    sql_password_permissions_repository,
):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.grant_access(user_id, password_id, PasswordPermission.READ)

    # When
    result = sql_password_permissions_repository.has_access_ignoring_expiry(
        user_id, password_id, PasswordPermission.READ
    )

    # Then
    assert result is True


def test_has_access_ignoring_expiry_returns_false_for_no_permission(
    sql_password_permissions_repository,
):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    result = sql_password_permissions_repository.has_access_ignoring_expiry(
        user_id, password_id, PasswordPermission.READ
    )

    # Then
    assert result is False


def test_grant_access_creates_permission(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    sql_password_permissions_repository.grant_access(user_id, password_id, PasswordPermission.READ)

    # Then
    assert sql_password_permissions_repository.has_access_ignoring_expiry(user_id, password_id, PasswordPermission.READ)


def test_grant_access_is_idempotent(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    sql_password_permissions_repository.grant_access(user_id, password_id, PasswordPermission.READ)
    sql_password_permissions_repository.grant_access(user_id, password_id, PasswordPermission.READ)

    # Then - no exception should be raised
    assert sql_password_permissions_repository.has_access_ignoring_expiry(user_id, password_id, PasswordPermission.READ)


def test_revoke_access_removes_permission(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.grant_access(user_id, password_id, PasswordPermission.READ)

    # When
    sql_password_permissions_repository.revoke_access(user_id, password_id)

    # Then
    assert not sql_password_permissions_repository.has_access_ignoring_expiry(
        user_id, password_id, PasswordPermission.READ
    )


def test_revoke_access_is_idempotent(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.grant_access(user_id, password_id, PasswordPermission.READ)

    # When
    sql_password_permissions_repository.revoke_access(user_id, password_id)
    sql_password_permissions_repository.revoke_access(user_id, password_id)

    # Then - no exception should be raised
    assert not sql_password_permissions_repository.has_access_ignoring_expiry(
        user_id, password_id, PasswordPermission.READ
    )


def test_list_all_permissions_for_empty_password(sql_password_permissions_repository):
    # Given
    password_id = uuid4()

    # When
    result = sql_password_permissions_repository.list_all_permissions_for(password_id)

    # Then
    assert result == {}


def test_list_all_permissions_for_multiple_users(sql_password_permissions_repository):
    # Given
    owner_id = uuid4()
    user1_id = uuid4()
    user2_id = uuid4()
    password_id = uuid4()

    sql_password_permissions_repository.set_owner(owner_id, password_id)
    sql_password_permissions_repository.grant_access(user1_id, password_id, PasswordPermission.READ)
    sql_password_permissions_repository.grant_access(user2_id, password_id, PasswordPermission.READ)

    # When
    result = sql_password_permissions_repository.list_all_permissions_for(password_id)

    # Then
    assert owner_id in result
    assert user1_id in result
    assert user2_id in result
    assert result[owner_id].is_owner is True
    assert PasswordPermission.READ in result[user1_id].permissions
    assert PasswordPermission.READ in result[user2_id].permissions


# Method: revoke_all_access_for_owner_group
def test_should_revoke_all_access_when_revoking_for_owner_group(
    sql_password_permissions_repository,
):
    # Given
    owner_group_id = uuid4()
    other_group_id = uuid4()
    password1_id = uuid4()
    password2_id = uuid4()
    password3_id = uuid4()

    # Set owner and grant permissions for multiple passwords
    sql_password_permissions_repository.set_owner(owner_group_id, password1_id)
    sql_password_permissions_repository.set_owner(owner_group_id, password2_id)
    sql_password_permissions_repository.set_owner(owner_group_id, password3_id)

    sql_password_permissions_repository.grant_access(other_group_id, password1_id, PasswordPermission.READ)
    sql_password_permissions_repository.grant_access(other_group_id, password2_id, PasswordPermission.READ)

    # When
    sql_password_permissions_repository.revoke_all_access_for_owner_group(owner_group_id)

    # Then - all ownerships and permissions for these passwords should be revoked
    assert not sql_password_permissions_repository.is_owner(owner_group_id, password1_id)
    assert not sql_password_permissions_repository.is_owner(owner_group_id, password2_id)
    assert not sql_password_permissions_repository.is_owner(owner_group_id, password3_id)
    assert not sql_password_permissions_repository.has_access_ignoring_expiry(
        other_group_id, password1_id, PasswordPermission.READ
    )
    assert not sql_password_permissions_repository.has_access_ignoring_expiry(
        other_group_id, password2_id, PasswordPermission.READ
    )


def test_should_not_affect_other_passwords_when_revoking_for_owner_group(
    sql_password_permissions_repository,
):
    # Given
    group1_id = uuid4()
    group2_id = uuid4()
    password1_id = uuid4()
    password2_id = uuid4()

    sql_password_permissions_repository.set_owner(group1_id, password1_id)
    sql_password_permissions_repository.set_owner(group2_id, password2_id)
    sql_password_permissions_repository.grant_access(group2_id, password1_id, PasswordPermission.READ)

    # When
    sql_password_permissions_repository.revoke_all_access_for_owner_group(group1_id)

    # Then - password2 owned by group2 should remain intact
    assert sql_password_permissions_repository.is_owner(group2_id, password2_id)
    assert not sql_password_permissions_repository.is_owner(group1_id, password1_id)
    assert not sql_password_permissions_repository.has_access_ignoring_expiry(
        group2_id, password1_id, PasswordPermission.READ
    )


def test_should_do_nothing_when_revoking_for_owner_group_with_no_passwords(
    sql_password_permissions_repository,
):
    # Given
    group_id = uuid4()

    # When / Then - should not raise any exception
    sql_password_permissions_repository.revoke_all_access_for_owner_group(group_id)


# Method: list_all_permissions_for_bulk
def test_should_return_empty_dict_when_called_with_empty_list(
    sql_password_permissions_repository,
):
    # When
    result = sql_password_permissions_repository.list_all_permissions_for_bulk([])

    # Then
    assert result == {}


def test_should_return_empty_permissions_for_each_password_when_none_exist(
    sql_password_permissions_repository,
):
    # Given
    password_id_1 = uuid4()
    password_id_2 = uuid4()

    # When
    result = sql_password_permissions_repository.list_all_permissions_for_bulk([password_id_1, password_id_2])

    # Then
    assert result == {password_id_1: {}, password_id_2: {}}


def test_should_return_owner_for_password_in_bulk(
    sql_password_permissions_repository,
):
    # Given
    owner_group_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.set_owner(owner_group_id, password_id)

    # When
    result = sql_password_permissions_repository.list_all_permissions_for_bulk([password_id])

    # Then
    assert password_id in result
    assert owner_group_id in result[password_id]
    owner_access = result[password_id][owner_group_id]
    assert owner_access.is_owner is True
    assert owner_access.permissions == set()


def test_should_return_correct_permissions_for_multiple_passwords_in_single_call(
    sql_password_permissions_repository,
):
    # Given
    owner_group_id = uuid4()
    shared_group_id = uuid4()
    password_id_1 = uuid4()
    password_id_2 = uuid4()

    sql_password_permissions_repository.set_owner(owner_group_id, password_id_1)
    sql_password_permissions_repository.set_owner(owner_group_id, password_id_2)
    sql_password_permissions_repository.grant_access(shared_group_id, password_id_1, PasswordPermission.READ)

    # When
    result = sql_password_permissions_repository.list_all_permissions_for_bulk([password_id_1, password_id_2])

    # Then
    assert owner_group_id in result[password_id_1]
    assert result[password_id_1][owner_group_id].is_owner is True

    assert shared_group_id in result[password_id_1]
    assert result[password_id_1][shared_group_id].is_owner is False
    assert PasswordPermission.READ in result[password_id_1][shared_group_id].permissions

    assert owner_group_id in result[password_id_2]
    assert result[password_id_2][owner_group_id].is_owner is True
    assert shared_group_id not in result[password_id_2]


def test_should_not_include_permissions_of_passwords_outside_the_requested_list(
    sql_password_permissions_repository,
):
    # Given
    group_id = uuid4()
    requested_password_id = uuid4()
    other_password_id = uuid4()

    sql_password_permissions_repository.set_owner(group_id, other_password_id)

    # When
    result = sql_password_permissions_repository.list_all_permissions_for_bulk([requested_password_id])

    # Then
    assert result == {requested_password_id: {}}
    assert other_password_id not in result


def test_should_match_list_all_permissions_for_called_individually(
    sql_password_permissions_repository,
):
    # Given
    owner_group_id = uuid4()
    shared_group_id = uuid4()
    password_id_1 = uuid4()
    password_id_2 = uuid4()

    sql_password_permissions_repository.set_owner(owner_group_id, password_id_1)
    sql_password_permissions_repository.set_owner(owner_group_id, password_id_2)
    sql_password_permissions_repository.grant_access(shared_group_id, password_id_2, PasswordPermission.READ)

    # When
    bulk_result = sql_password_permissions_repository.list_all_permissions_for_bulk([password_id_1, password_id_2])
    single_result_1 = sql_password_permissions_repository.list_all_permissions_for(password_id_1)
    single_result_2 = sql_password_permissions_repository.list_all_permissions_for(password_id_2)

    # Then
    assert bulk_result[password_id_1] == single_result_1
    assert bulk_result[password_id_2] == single_result_2


# ── Temporary shares ──────────────────────────────────────────────────


def test_should_store_a_share_as_permanent_by_default(sql_password_permissions_repository):
    # Given
    group_id, password_id = uuid4(), uuid4()

    # When
    sql_password_permissions_repository.grant_access(group_id, password_id, PasswordPermission.READ)

    # Then
    result = sql_password_permissions_repository.list_all_permissions_for(password_id)
    assert result[group_id].expires_at is None


def test_should_round_trip_an_expiry_as_aware_utc(sql_password_permissions_repository):
    """The column is naive, so a reloaded row must come back with UTC re-attached."""
    # Given
    group_id, password_id = uuid4(), uuid4()
    expires_at = datetime(2026, 6, 1, 8, 0, 0, tzinfo=UTC)

    # When
    sql_password_permissions_repository.grant_access(group_id, password_id, PasswordPermission.READ, expires_at)

    # Then
    stored = sql_password_permissions_repository.list_all_permissions_for(password_id)[group_id].expires_at
    assert stored == expires_at
    assert stored.tzinfo is not None


def test_should_normalise_an_offset_expiry_to_the_same_instant(sql_password_permissions_repository):
    """A wall clock stored without its offset would move the deadline by the offset."""
    # Given
    group_id, password_id = uuid4(), uuid4()
    paris_noon = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))

    # When
    sql_password_permissions_repository.grant_access(group_id, password_id, PasswordPermission.READ, paris_noon)

    # Then
    stored = sql_password_permissions_repository.list_all_permissions_for(password_id)[group_id].expires_at
    assert stored == datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)


def test_should_carry_the_expiry_through_the_bulk_read(sql_password_permissions_repository):
    # Given
    group_id, password_id = uuid4(), uuid4()
    expires_at = datetime(2026, 6, 1, 8, 0, 0, tzinfo=UTC)
    sql_password_permissions_repository.grant_access(group_id, password_id, PasswordPermission.READ, expires_at)

    # When
    result = sql_password_permissions_repository.list_all_permissions_for_bulk([password_id])

    # Then
    assert result[password_id][group_id].expires_at == expires_at


def test_should_overwrite_the_expiry_when_re_granting_access(sql_password_permissions_repository):
    """Re-sharing is how a duration is changed; the row must not be left untouched."""
    # Given
    group_id, password_id = uuid4(), uuid4()
    sql_password_permissions_repository.grant_access(
        group_id, password_id, PasswordPermission.READ, datetime(2026, 6, 1, tzinfo=UTC)
    )

    # When
    sql_password_permissions_repository.grant_access(
        group_id, password_id, PasswordPermission.READ, datetime(2026, 9, 1, tzinfo=UTC)
    )

    # Then
    result = sql_password_permissions_repository.list_all_permissions_for(password_id)
    assert result[group_id].expires_at == datetime(2026, 9, 1, tzinfo=UTC)


def test_should_drop_the_expiry_when_re_granting_without_one(sql_password_permissions_repository):
    # Given
    group_id, password_id = uuid4(), uuid4()
    sql_password_permissions_repository.grant_access(
        group_id, password_id, PasswordPermission.READ, datetime(2026, 6, 1, tzinfo=UTC)
    )

    # When
    sql_password_permissions_repository.grant_access(group_id, password_id, PasswordPermission.READ)

    # Then
    assert sql_password_permissions_repository.list_all_permissions_for(password_id)[group_id].expires_at is None


def test_should_update_the_expiration_of_an_existing_share(sql_password_permissions_repository):
    # Given
    group_id, password_id = uuid4(), uuid4()
    sql_password_permissions_repository.grant_access(group_id, password_id, PasswordPermission.READ)

    # When
    updated = sql_password_permissions_repository.update_access_expiration(
        group_id, password_id, datetime(2026, 6, 1, tzinfo=UTC)
    )

    # Then
    assert updated is True
    result = sql_password_permissions_repository.list_all_permissions_for(password_id)
    assert result[group_id].expires_at == datetime(2026, 6, 1, tzinfo=UTC)


def test_should_make_a_temporary_share_permanent(sql_password_permissions_repository):
    # Given
    group_id, password_id = uuid4(), uuid4()
    sql_password_permissions_repository.grant_access(
        group_id, password_id, PasswordPermission.READ, datetime(2026, 6, 1, tzinfo=UTC)
    )

    # When
    updated = sql_password_permissions_repository.update_access_expiration(group_id, password_id, None)

    # Then
    assert updated is True
    assert sql_password_permissions_repository.list_all_permissions_for(password_id)[group_id].expires_at is None


def test_should_report_no_update_when_the_group_holds_no_share(sql_password_permissions_repository):
    # Given
    password_id = uuid4()
    sql_password_permissions_repository.set_owner(uuid4(), password_id)

    # When
    updated = sql_password_permissions_repository.update_access_expiration(
        uuid4(), password_id, datetime(2026, 6, 1, tzinfo=UTC)
    )

    # Then
    assert updated is False


def test_should_not_turn_an_owner_into_a_temporary_share(sql_password_permissions_repository):
    """Ownership lives in its own table, so it has no expiry to update."""
    # Given
    owner_group_id, password_id = uuid4(), uuid4()
    sql_password_permissions_repository.set_owner(owner_group_id, password_id)

    # When
    updated = sql_password_permissions_repository.update_access_expiration(
        owner_group_id, password_id, datetime(2026, 6, 1, tzinfo=UTC)
    )

    # Then
    assert updated is False
    assert sql_password_permissions_repository.list_all_permissions_for(password_id)[owner_group_id].expires_at is None


def test_should_purge_only_shares_expired_before_the_cutoff(sql_password_permissions_repository):
    # Given
    password_id = uuid4()
    long_gone, recently_expired, still_alive, permanent = uuid4(), uuid4(), uuid4(), uuid4()
    sql_password_permissions_repository.set_owner(uuid4(), password_id)
    sql_password_permissions_repository.grant_access(
        long_gone, password_id, PasswordPermission.READ, datetime(2026, 1, 1, tzinfo=UTC)
    )
    sql_password_permissions_repository.grant_access(
        recently_expired, password_id, PasswordPermission.READ, datetime(2026, 6, 25, tzinfo=UTC)
    )
    sql_password_permissions_repository.grant_access(
        still_alive, password_id, PasswordPermission.READ, datetime(2026, 12, 1, tzinfo=UTC)
    )
    sql_password_permissions_repository.grant_access(permanent, password_id, PasswordPermission.READ)

    # When
    deleted = sql_password_permissions_repository.purge_expired_shares(datetime(2026, 6, 20, tzinfo=UTC))

    # Then
    assert deleted == 1
    remaining = sql_password_permissions_repository.list_all_permissions_for(password_id)
    assert long_gone not in remaining
    assert recently_expired in remaining
    assert still_alive in remaining
    assert permanent in remaining


def test_should_purge_nothing_when_no_share_is_old_enough(sql_password_permissions_repository):
    # Given
    group_id, password_id = uuid4(), uuid4()
    sql_password_permissions_repository.grant_access(group_id, password_id, PasswordPermission.READ)

    # When
    deleted = sql_password_permissions_repository.purge_expired_shares(datetime(2030, 1, 1, tzinfo=UTC))

    # Then
    assert deleted == 0
    assert group_id in sql_password_permissions_repository.list_all_permissions_for(password_id)
