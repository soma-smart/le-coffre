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
