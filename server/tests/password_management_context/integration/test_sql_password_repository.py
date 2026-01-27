import pytest
from uuid import uuid4
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import PasswordNotFoundError


def test_should_save_and_retrieve_password_when_valid_data_provided(
    sql_password_repository,
):
    password_id = uuid4()
    password = Password(
        id=password_id, name="Test", encrypted_value="abc", folder="default"
    )
    sql_password_repository.save(password)
    retrieved = sql_password_repository.get_by_id(password_id)
    assert retrieved is not None
    assert retrieved.id == password_id
    assert retrieved.name == "Test"


def test_should_update_password_when_password_exists(sql_password_repository):
    password_id = uuid4()
    password = Password(
        id=password_id, name="Old", encrypted_value="abc", folder="default"
    )
    sql_password_repository.save(password)
    password.name = "New"
    sql_password_repository.update(password)
    updated = sql_password_repository.get_by_id(password_id)
    assert updated.name == "New"


def test_should_raise_error_when_updating_nonexistent_password(sql_password_repository):
    non_existent_id = uuid4()
    password = Password(
        id=non_existent_id, name="NonExistent", encrypted_value="abc", folder="default"
    )
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.update(password)


def test_should_delete_password_when_password_exists(sql_password_repository):
    password_id = uuid4()
    password = Password(
        id=password_id, name="ToDelete", encrypted_value="abc", folder="default"
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
        Password(id=uuid4(), name=f"Pwd{i}", encrypted_value="enc", folder="default")
        for i in range(4)
    ]
    folder_password = Password(
        id=uuid4(), name="nofolderpwd", encrypted_value="enc", folder="folder1"
    )
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
            id=uuid4(), name=f"Pwd{i}", encrypted_value="enc", folder="folder_test"
        )
        for i in range(4)
    ]
    folder_name = "folder_test"
    for pwd in passwords:
        sql_password_repository.save(pwd)
    non_folder_password = Password(
        id=uuid4(), name="NoFolder", encrypted_value="enc", folder="default"
    )
    sql_password_repository.save(non_folder_password)

    all_passwords = sql_password_repository.list_all(folder=folder_name)

    assert len(all_passwords) == len(passwords)
    retrieved_ids = {pwd.id for pwd in all_passwords}
    for pwd in passwords:
        assert pwd.id in retrieved_ids


def test_should_return_all_saved_passwords_when_listing(sql_password_repository):
    passwords = [
        Password(id=uuid4(), name=f"Pwd{i}", encrypted_value="enc", folder="default")
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
