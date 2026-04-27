from uuid import uuid4

import pytest

from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)


def test_should_save_and_retrieve_user_when_valid_data_provided(sql_user_repository):
    test_user = User(
        id=uuid4(),
        username="testuser",
        email="test@test.fr",
        name="Test User",
        roles=[],
    )
    sql_user_repository.save(test_user)
    retrieved_user = sql_user_repository.get_by_id(test_user.id)
    assert retrieved_user is not None
    assert retrieved_user.id == test_user.id
    assert retrieved_user.username == test_user.username
    assert retrieved_user.email == test_user.email
    assert retrieved_user.name == test_user.name
    assert retrieved_user.roles == test_user.roles


def test_should_list_all_users_when_multiple_users_exist(sql_user_repository):
    user1 = User(id=uuid4(), username="user1", email="test1@test.fr", name="User One", roles=[])
    user2 = User(id=uuid4(), username="user2", email="test2@test.fr", name="User Two", roles=[])
    sql_user_repository.save(user1)
    sql_user_repository.save(user2)
    users = sql_user_repository.list_all()
    assert len(users) == 2
    user_ids = [user.id for user in users]
    assert user1.id in user_ids
    assert user2.id in user_ids


def test_should_delete_user_when_user_exists(sql_user_repository):
    user_to_delete = User(
        id=uuid4(),
        username="tobedeleted",
        email="test@test.fr",
        name="To Be Deleted",
        roles=[],
    )
    sql_user_repository.save(user_to_delete)
    sql_user_repository.delete(user_to_delete.id)
    deleted_user = sql_user_repository.get_by_id(user_to_delete.id)
    assert deleted_user is None


def test_should_return_none_when_getting_nonexistent_user(sql_user_repository):
    non_existent_user = User(
        id=uuid4(),
        username="nonexistent",
        email="test@test.fr",
        name="Non Existent",
        roles=[],
    )
    result = sql_user_repository.get_by_id(non_existent_user.id)
    assert result is None


def test_should_raise_error_when_saving_existing_user(sql_user_repository):
    existing_user = User(
        id=uuid4(),
        username="existinguser",
        email="test@test.fr",
        name="Existing User",
        roles=[],
    )
    sql_user_repository.save(existing_user)
    with pytest.raises(UserAlreadyExistsError):
        sql_user_repository.save(existing_user)


def test_should_return_zero_when_no_users_exist(sql_user_repository):
    count = sql_user_repository.count()
    assert count == 0


def test_should_return_correct_count_when_one_user_exists(sql_user_repository):
    user = User(id=uuid4(), username="user1", email="user1@test.fr", name="User One", roles=[])
    sql_user_repository.save(user)

    count = sql_user_repository.count()

    assert count == 1


def test_should_return_correct_count_when_multiple_users_exist(sql_user_repository):
    user1 = User(id=uuid4(), username="user1", email="user1@test.fr", name="User One", roles=[])
    user2 = User(id=uuid4(), username="user2", email="user2@test.fr", name="User Two", roles=[])
    user3 = User(id=uuid4(), username="user3", email="user3@test.fr", name="User Three", roles=[])
    sql_user_repository.save(user1)
    sql_user_repository.save(user2)
    sql_user_repository.save(user3)

    count = sql_user_repository.count()

    assert count == 3


def test_should_return_updated_count_after_deletion(sql_user_repository):
    user1 = User(id=uuid4(), username="user1", email="user1@test.fr", name="User One", roles=[])
    user2 = User(id=uuid4(), username="user2", email="user2@test.fr", name="User Two", roles=[])
    sql_user_repository.save(user1)
    sql_user_repository.save(user2)

    sql_user_repository.delete(user1.id)
    count = sql_user_repository.count()

    assert count == 1


def test_should_update_user_when_user_exists(sql_user_repository):
    user_to_update = User(
        id=uuid4(),
        username="updatableuser",
        email="testupdate@test.fr",
        name="Updatable User",
        roles=[],
    )
    sql_user_repository.save(user_to_update)
    user_to_update.name = "Updated User"
    sql_user_repository.update(user_to_update)
    updated_user = sql_user_repository.get_by_id(user_to_update.id)
    assert updated_user.name == "Updated User"


def test_should_raise_error_when_updating_nonexistent_user(sql_user_repository):
    non_existent_user = User(
        id=uuid4(),
        username="existinguser",
        email="test@test.fr",
        name="Existing User",
        roles=[],
    )
    non_existent_user.name = "Updated non existent user"
    with pytest.raises(UserNotFoundError):
        sql_user_repository.update(non_existent_user)


def test_should_retrieve_admin_user_when_admin_exists(sql_user_repository):
    admin_user = User(
        id=uuid4(),
        username="adminuser",
        email="admin@example.com",
        name="Admin User",
        roles=["admin"],
    )
    normal_user = User(
        id=uuid4(),
        username="normaluser",
        email="normal@example.com",
        name="Normal User",
        roles=["user"],
    )
    sql_user_repository.save(admin_user)
    sql_user_repository.save(normal_user)
    retrieved_admin = sql_user_repository.get_admin()
    assert retrieved_admin is not None
    assert retrieved_admin.id == admin_user.id
    assert retrieved_admin.username == admin_user.username
    assert retrieved_admin.email == admin_user.email
    assert retrieved_admin.name == admin_user.name
    assert retrieved_admin.roles == admin_user.roles
