from uuid import uuid4

from rights_access_context.domain.value_objects import Permission


def test_given_user_and_resource_when_adding_read_permission_then_permission_is_stored(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()

    # Act
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)

    # Assert
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.READ)


def test_given_user_and_resource_when_adding_multiple_permissions_then_all_permissions_are_stored(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()

    # Act
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)
    sql_rights_repository.add_permission(user_id, resource_id, Permission.UPDATE)
    sql_rights_repository.add_permission(user_id, resource_id, Permission.DELETE)

    # Assert
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.READ)
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.UPDATE)
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.DELETE)


def test_given_user_with_permission_when_removing_permission_then_permission_is_removed(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)

    # Act
    sql_rights_repository.remove_permission(user_id, resource_id, Permission.READ)

    # Assert
    assert not sql_rights_repository.has_permission(
        user_id, resource_id, Permission.READ
    )


def test_given_user_with_multiple_permissions_when_removing_one_permission_then_only_that_permission_is_removed(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)
    sql_rights_repository.add_permission(user_id, resource_id, Permission.UPDATE)

    # Act
    sql_rights_repository.remove_permission(user_id, resource_id, Permission.READ)

    # Assert
    assert not sql_rights_repository.has_permission(
        user_id, resource_id, Permission.READ
    )
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.UPDATE)


def test_given_no_permission_when_removing_permission_then_no_error_occurs(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()

    # Act & Assert - should not raise any exception
    sql_rights_repository.remove_permission(user_id, resource_id, Permission.READ)


def test_given_user_with_permission_when_checking_permission_then_returns_true(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)

    # Act
    result = sql_rights_repository.has_permission(user_id, resource_id, Permission.READ)

    # Assert
    assert result is True


def test_given_user_without_permission_when_checking_permission_then_returns_false(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()

    # Act
    result = sql_rights_repository.has_permission(user_id, resource_id, Permission.READ)

    # Assert
    assert result is False


def test_given_owner_when_checking_any_permission_then_returns_true(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.set_owner(user_id, resource_id)

    # Act & Assert
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.READ)
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.UPDATE)
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.DELETE)


def test_given_user_with_different_permission_when_checking_another_permission_then_returns_false(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)

    # Act
    result = sql_rights_repository.has_permission(
        user_id, resource_id, Permission.UPDATE
    )

    # Assert
    assert result is False


def test_given_user_with_single_permission_when_getting_all_permissions_then_returns_set_with_that_permission(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)

    # Act
    permissions = sql_rights_repository.get_all_permissions(user_id, resource_id)

    # Assert
    assert permissions == {Permission.READ}


def test_given_user_with_multiple_permissions_when_getting_all_permissions_then_returns_set_with_all_permissions(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)
    sql_rights_repository.add_permission(user_id, resource_id, Permission.UPDATE)
    sql_rights_repository.add_permission(user_id, resource_id, Permission.DELETE)

    # Act
    permissions = sql_rights_repository.get_all_permissions(user_id, resource_id)

    # Assert
    assert permissions == {Permission.READ, Permission.UPDATE, Permission.DELETE}


def test_given_user_and_resource_when_setting_owner_then_ownership_is_stored(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()

    # Act
    sql_rights_repository.set_owner(user_id, resource_id)

    # Assert
    assert sql_rights_repository.is_owner(user_id, resource_id)


def test_given_multiple_users_when_setting_different_owners_for_different_resources_then_all_ownerships_are_stored(
    sql_rights_repository,
):
    # Arrange
    user1_id = uuid4()
    user2_id = uuid4()
    resource1_id = uuid4()
    resource2_id = uuid4()

    # Act
    sql_rights_repository.set_owner(user1_id, resource1_id)
    sql_rights_repository.set_owner(user2_id, resource2_id)

    # Assert
    assert sql_rights_repository.is_owner(user1_id, resource1_id)
    assert sql_rights_repository.is_owner(user2_id, resource2_id)
    assert not sql_rights_repository.is_owner(user1_id, resource2_id)
    assert not sql_rights_repository.is_owner(user2_id, resource1_id)


def test_given_user_is_owner_when_checking_ownership_then_returns_true(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.set_owner(user_id, resource_id)

    # Act
    result = sql_rights_repository.is_owner(user_id, resource_id)

    # Assert
    assert result is True


def test_given_user_is_not_owner_when_checking_ownership_then_returns_false(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()

    # Act
    result = sql_rights_repository.is_owner(user_id, resource_id)

    # Assert
    assert result is False


def test_given_owner_with_explicit_permissions_when_removing_permissions_then_owner_still_has_access(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource_id = uuid4()
    sql_rights_repository.set_owner(user_id, resource_id)
    sql_rights_repository.add_permission(user_id, resource_id, Permission.READ)

    # Act
    sql_rights_repository.remove_permission(user_id, resource_id, Permission.READ)

    # Assert - owner should still have access through ownership
    assert sql_rights_repository.has_permission(user_id, resource_id, Permission.READ)


def test_given_user_with_permissions_on_multiple_resources_when_querying_then_permissions_are_isolated_per_resource(
    sql_rights_repository,
):
    # Arrange
    user_id = uuid4()
    resource1_id = uuid4()
    resource2_id = uuid4()

    # Act
    sql_rights_repository.add_permission(user_id, resource1_id, Permission.READ)
    sql_rights_repository.add_permission(user_id, resource2_id, Permission.UPDATE)

    # Assert
    assert sql_rights_repository.has_permission(user_id, resource1_id, Permission.READ)
    assert not sql_rights_repository.has_permission(
        user_id, resource1_id, Permission.UPDATE
    )
    assert sql_rights_repository.has_permission(
        user_id, resource2_id, Permission.UPDATE
    )
    assert not sql_rights_repository.has_permission(
        user_id, resource2_id, Permission.READ
    )
