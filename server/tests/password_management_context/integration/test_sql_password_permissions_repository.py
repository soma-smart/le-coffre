import pytest
from uuid import uuid4

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


def test_has_access_returns_true_for_owner(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.set_owner(user_id, password_id)

    # When
    result = sql_password_permissions_repository.has_access(
        user_id, password_id, PasswordPermission.READ
    )

    # Then
    assert result is True


def test_has_access_returns_true_for_granted_permission(
    sql_password_permissions_repository,
):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.grant_access(
        user_id, password_id, PasswordPermission.READ
    )

    # When
    result = sql_password_permissions_repository.has_access(
        user_id, password_id, PasswordPermission.READ
    )

    # Then
    assert result is True


def test_has_access_returns_false_for_no_permission(
    sql_password_permissions_repository,
):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    result = sql_password_permissions_repository.has_access(
        user_id, password_id, PasswordPermission.READ
    )

    # Then
    assert result is False


def test_grant_access_creates_permission(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    sql_password_permissions_repository.grant_access(
        user_id, password_id, PasswordPermission.READ
    )

    # Then
    assert sql_password_permissions_repository.has_access(
        user_id, password_id, PasswordPermission.READ
    )


def test_grant_access_is_idempotent(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()

    # When
    sql_password_permissions_repository.grant_access(
        user_id, password_id, PasswordPermission.READ
    )
    sql_password_permissions_repository.grant_access(
        user_id, password_id, PasswordPermission.READ
    )

    # Then - no exception should be raised
    assert sql_password_permissions_repository.has_access(
        user_id, password_id, PasswordPermission.READ
    )


def test_revoke_access_removes_permission(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.grant_access(
        user_id, password_id, PasswordPermission.READ
    )

    # When
    sql_password_permissions_repository.revoke_access(user_id, password_id)

    # Then
    assert not sql_password_permissions_repository.has_access(
        user_id, password_id, PasswordPermission.READ
    )


def test_revoke_access_is_idempotent(sql_password_permissions_repository):
    # Given
    user_id = uuid4()
    password_id = uuid4()
    sql_password_permissions_repository.grant_access(
        user_id, password_id, PasswordPermission.READ
    )

    # When
    sql_password_permissions_repository.revoke_access(user_id, password_id)
    sql_password_permissions_repository.revoke_access(user_id, password_id)

    # Then - no exception should be raised
    assert not sql_password_permissions_repository.has_access(
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
    sql_password_permissions_repository.grant_access(
        user1_id, password_id, PasswordPermission.READ
    )
    sql_password_permissions_repository.grant_access(
        user2_id, password_id, PasswordPermission.READ
    )

    # When
    result = sql_password_permissions_repository.list_all_permissions_for(password_id)

    # Then
    assert owner_id in result
    assert user1_id in result
    assert user2_id in result
    assert result[owner_id][0] is True
    assert PasswordPermission.READ in result[user1_id][1]
    assert PasswordPermission.READ in result[user2_id][1]


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

    sql_password_permissions_repository.grant_access(
        other_group_id, password1_id, PasswordPermission.READ
    )
    sql_password_permissions_repository.grant_access(
        other_group_id, password2_id, PasswordPermission.READ
    )

    # When
    sql_password_permissions_repository.revoke_all_access_for_owner_group(
        owner_group_id
    )

    # Then - all ownerships and permissions for these passwords should be revoked
    assert not sql_password_permissions_repository.is_owner(
        owner_group_id, password1_id
    )
    assert not sql_password_permissions_repository.is_owner(
        owner_group_id, password2_id
    )
    assert not sql_password_permissions_repository.is_owner(
        owner_group_id, password3_id
    )
    assert not sql_password_permissions_repository.has_access(
        other_group_id, password1_id, PasswordPermission.READ
    )
    assert not sql_password_permissions_repository.has_access(
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
    sql_password_permissions_repository.grant_access(
        group2_id, password1_id, PasswordPermission.READ
    )

    # When
    sql_password_permissions_repository.revoke_all_access_for_owner_group(group1_id)

    # Then - password2 owned by group2 should remain intact
    assert sql_password_permissions_repository.is_owner(group2_id, password2_id)
    assert not sql_password_permissions_repository.is_owner(group1_id, password1_id)
    assert not sql_password_permissions_repository.has_access(
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
    result = sql_password_permissions_repository.list_all_permissions_for_bulk(
        [password_id_1, password_id_2]
    )

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
    result = sql_password_permissions_repository.list_all_permissions_for_bulk(
        [password_id]
    )

    # Then
    assert password_id in result
    assert owner_group_id in result[password_id]
    is_owner, permissions = result[password_id][owner_group_id]
    assert is_owner is True
    assert permissions == set()


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
    sql_password_permissions_repository.grant_access(
        shared_group_id, password_id_1, PasswordPermission.READ
    )

    # When
    result = sql_password_permissions_repository.list_all_permissions_for_bulk(
        [password_id_1, password_id_2]
    )

    # Then
    assert owner_group_id in result[password_id_1]
    assert result[password_id_1][owner_group_id][0] is True

    assert shared_group_id in result[password_id_1]
    assert result[password_id_1][shared_group_id][0] is False
    assert PasswordPermission.READ in result[password_id_1][shared_group_id][1]

    assert owner_group_id in result[password_id_2]
    assert result[password_id_2][owner_group_id][0] is True
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
    result = sql_password_permissions_repository.list_all_permissions_for_bulk(
        [requested_password_id]
    )

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
    sql_password_permissions_repository.grant_access(
        shared_group_id, password_id_2, PasswordPermission.READ
    )

    # When
    bulk_result = sql_password_permissions_repository.list_all_permissions_for_bulk(
        [password_id_1, password_id_2]
    )
    single_result_1 = sql_password_permissions_repository.list_all_permissions_for(
        password_id_1
    )
    single_result_2 = sql_password_permissions_repository.list_all_permissions_for(
        password_id_2
    )

    # Then
    assert bulk_result[password_id_1] == single_result_1
    assert bulk_result[password_id_2] == single_result_2
