from uuid import uuid4

import pytest

from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import PasswordNotFoundError


def test_should_save_and_retrieve_password_when_valid_data_provided(
    sql_password_repository,
):
    password_id = uuid4()
    password = Password(
        id=password_id,
        name="Test",
        encrypted_value="abc",
        folder="default",
        url="http://example.com",
        login="user1",
    )
    sql_password_repository.save(password)
    retrieved = sql_password_repository.get_by_id(password_id)
    assert retrieved is not None
    assert retrieved.id == password_id
    assert retrieved.name == "Test"
    assert retrieved.url == "http://example.com"
    assert retrieved.login == "user1"


def test_should_update_password_when_password_exists(sql_password_repository):
    password_id = uuid4()
    password = Password(
        id=password_id,
        name="Old",
        encrypted_value="abc",
        folder="default",
        url="http://example.com",
        login="user1",
    )
    sql_password_repository.save(password)
    password.name = "New"
    password.url = "http://newexample.com"
    password.login = "newuser1"
    sql_password_repository.update(password)
    updated = sql_password_repository.get_by_id(password_id)
    assert updated.name == "New"
    assert updated.url == "http://newexample.com"
    assert updated.login == "newuser1"


def test_should_raise_error_when_updating_nonexistent_password(sql_password_repository):
    non_existent_id = uuid4()
    password = Password(
        id=non_existent_id,
        name="NonExistent",
        encrypted_value="abc",
        folder="default",
        url="http://example.com",
        login="user1",
    )
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.update(password)


def test_should_delete_password_when_password_exists(sql_password_repository):
    password_id = uuid4()
    password = Password(
        id=password_id,
        name="ToDelete",
        encrypted_value="abc",
        folder="default",
        url="http://example.com",
        login="user1",
    )
    sql_password_repository.save(password)
    sql_password_repository.delete(password_id)
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.get_by_id(password_id)


def test_should_raise_error_when_deleting_nonexistent_password(sql_password_repository):
    non_existent_id = uuid4()
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.delete(non_existent_id)


def test_should_list_all_passwords_when_no_folder_filter(sql_password_repository):
    passwords = [
        Password(
            id=uuid4(),
            name=f"Pwd{i}",
            encrypted_value="enc",
            folder="default",
            url=f"http://example_{i}.com",
            login=f"user{i}",
        )
        for i in range(4)
    ]
    folder_password = Password(id=uuid4(), name="nofolderpwd", encrypted_value="enc", folder="folder1")
    sql_password_repository.save(folder_password)
    for pwd in passwords:
        sql_password_repository.save(pwd)

    all_passwords = sql_password_repository.list_all()

    assert len(all_passwords) == 5
    retrieved_ids = {pwd.id for pwd in all_passwords}
    for pwd in passwords:
        assert pwd.id in retrieved_ids


def test_should_list_only_folder_passwords_when_folder_filter_provided(
    sql_password_repository,
):
    passwords = [
        Password(
            id=uuid4(),
            name=f"Pwd{i}",
            encrypted_value="enc",
            folder="folder_test",
            url=f"http://example_{i}.com",
            login=f"user{i}",
        )
        for i in range(4)
    ]
    folder_name = "folder_test"
    for pwd in passwords:
        sql_password_repository.save(pwd)
    non_folder_password = Password(
        id=uuid4(),
        name="NoFolder",
        encrypted_value="enc",
        folder="default",
        url="http://example.com",
        login="user",
    )
    sql_password_repository.save(non_folder_password)

    all_passwords = sql_password_repository.list_all(folder=folder_name)

    assert len(all_passwords) == len(passwords)
    retrieved_ids = {pwd.id for pwd in all_passwords}
    for pwd in passwords:
        assert pwd.id in retrieved_ids


def test_should_return_all_saved_passwords_when_listing(sql_password_repository):
    passwords = [
        Password(
            id=uuid4(),
            name=f"Pwd{i}",
            encrypted_value="enc",
            folder="default",
            url=f"http://example_{i}.com",
            login=f"user{i}",
        )
        for i in range(4)
    ]
    for pwd in passwords:
        sql_password_repository.save(pwd)
    all_passwords = sql_password_repository.list_all()
    assert len(all_passwords) == len(passwords)
    retrieved_ids = {pwd.id for pwd in all_passwords}
    for pwd in passwords:
        assert pwd.id in retrieved_ids


def test_should_return_empty_list_when_no_passwords_exist(sql_password_repository):
    passwords = sql_password_repository.list_all()
    assert len(passwords) == 0


def test_should_raise_error_when_getting_nonexistent_password(sql_password_repository):
    non_existent_id = uuid4()
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.get_by_id(non_existent_id)


# Method: delete_by_owner_group
def test_should_delete_all_passwords_when_deleting_by_owner_group(
    sql_password_repository, sql_password_permissions_repository
):
    # Given
    group_id = uuid4()
    password1_id = uuid4()
    password2_id = uuid4()
    password3_id = uuid4()

    # Create passwords
    password1 = Password(
        id=password1_id,
        name="Pwd1",
        encrypted_value="enc1",
        folder="default",
        url="http://example.1.com",
        login="user1",
    )
    password2 = Password(
        id=password2_id,
        name="Pwd2",
        encrypted_value="enc2",
        folder="default",
        url="http://example.2.com",
        login="user2",
    )
    password3 = Password(
        id=password3_id,
        name="Pwd3",
        encrypted_value="enc3",
        folder="default",
        url="http://example.3.com",
        login="user3",
    )
    sql_password_repository.save(password1)
    sql_password_repository.save(password2)
    sql_password_repository.save(password3)

    # Set group as owner
    sql_password_permissions_repository.set_owner(group_id, password1_id)
    sql_password_permissions_repository.set_owner(group_id, password2_id)
    sql_password_permissions_repository.set_owner(group_id, password3_id)

    # When
    sql_password_repository.delete_by_owner_group(group_id)

    # Then
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.get_by_id(password1_id)
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.get_by_id(password2_id)
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.get_by_id(password3_id)


def test_should_not_delete_passwords_owned_by_other_groups_when_deleting_by_owner_group(
    sql_password_repository, sql_password_permissions_repository
):
    # Given
    group1_id = uuid4()
    group2_id = uuid4()
    password1_id = uuid4()
    password2_id = uuid4()

    password1 = Password(
        id=password1_id,
        name="Pwd1",
        encrypted_value="enc1",
        folder="default",
        url="http://example.1.com",
        login="user1",
    )
    password2 = Password(
        id=password2_id,
        name="Pwd2",
        encrypted_value="enc2",
        folder="default",
        url="http://example.2.com",
        login="user2",
    )
    sql_password_repository.save(password1)
    sql_password_repository.save(password2)

    sql_password_permissions_repository.set_owner(group1_id, password1_id)
    sql_password_permissions_repository.set_owner(group2_id, password2_id)

    # When
    sql_password_repository.delete_by_owner_group(group1_id)

    # Then
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.get_by_id(password1_id)
    # password2 should still exist
    retrieved = sql_password_repository.get_by_id(password2_id)
    assert retrieved.id == password2_id


def test_should_do_nothing_when_deleting_by_owner_group_with_no_passwords(
    sql_password_repository,
):
    # Given
    group_id = uuid4()

    # When / Then - should not raise any exception
    sql_password_repository.delete_by_owner_group(group_id)


def test_should_return_zero_when_no_passwords_exist_for_count(sql_password_repository):
    count = sql_password_repository.count()
    assert count == 0


def test_should_return_correct_count_when_passwords_exist(sql_password_repository):
    for i in range(3):
        sql_password_repository.save(Password(id=uuid4(), name=f"Pwd{i}", encrypted_value="enc", folder="default"))
    count = sql_password_repository.count()
    assert count == 3
