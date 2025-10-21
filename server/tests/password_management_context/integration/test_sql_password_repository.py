import pytest
from uuid import uuid4
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import PasswordNotFoundError

@pytest.fixture(scope="function")
def test_save_and_get_by_id(sql_password_repository):
    password_id = uuid4()
    print("Created password ID:", password_id)
    password = Password(id=password_id, name="Test", encrypted_value="abc", folder=None)
    sql_password_repository.save(password)
    retrieved = sql_password_repository.get_by_id(password_id)
    assert retrieved is not None
    assert retrieved.id == password_id
    assert retrieved.name == "Test"

def test_update_password(sql_password_repository):
    password_id = uuid4()
    password = Password(id=password_id, name="Old", encrypted_value="abc", folder=None)
    sql_password_repository.save(password)
    password.name = "New"
    sql_password_repository.update(password)
    updated = sql_password_repository.get_by_id(password_id)
    assert updated.name == "New"

def test_delete_password(sql_password_repository):
    password_id = uuid4()
    password = Password(id=password_id, name="ToDelete", encrypted_value="abc", folder=None)
    sql_password_repository.save(password)
    sql_password_repository.delete(password_id)
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.get_by_id(password_id)

def test_list_all_without_folders(sql_password_repository, passwords = [Password(id=uuid4(), name=f"Pwd{i}", encrypted_value="enc", folder=None) for i in range(4)]):
    folder_password = Password(id=uuid4(), name=f"nofolderpwd", encrypted_value="enc", folder="folder1")
    sql_password_repository.save(folder_password)
    for pwd in passwords:
        sql_password_repository.save(pwd)
    all_passwords = sql_password_repository.list_all()
    no_folder_passwords = [pwd for pwd in all_passwords if pwd.folder is None]
    assert len(no_folder_passwords) == len(passwords)
    retrieved_ids = {pwd.id for pwd in no_folder_passwords}
    for pwd in passwords:
        assert pwd.id in retrieved_ids
        
def test_list_all_with_folder(sql_password_repository, passwords = [Password(id=uuid4(), name=f"Pwd{i}", encrypted_value="enc", folder="folder_test") for i in range(4)]):
    folder_name = "folder_test"
    for pwd in passwords:
        sql_password_repository.save(pwd)
    non_folder_password = Password(id=uuid4(), name="NoFolder", encrypted_value="enc", folder=None)
    sql_password_repository.save(non_folder_password)
    all_passwords = sql_password_repository.list_all(folder=folder_name)
    assert len(all_passwords) == len(passwords)
    all_non_folder_passwords = [pwd for pwd in sql_password_repository.list_all() if pwd.folder is None]
    assert len(all_non_folder_passwords) == 1
    retrieved_ids = {pwd.id for pwd in all_passwords}
    for pwd in passwords:
        assert pwd.id in retrieved_ids

def list_all_passwords(sql_password_repository, passwords = 4):
    for pwd in passwords:
        sql_password_repository.save(pwd)
    all_passwords = sql_password_repository.list_all()
    assert len(all_passwords) == len(passwords)
    retrieved_ids = {pwd.id for pwd in all_passwords}
    for pwd in passwords:
        assert pwd.id in retrieved_ids

def test_list_all_nonexistent(sql_password_repository):
    passwords = sql_password_repository.list_all()
    assert len(passwords) == 0
    
def test_get_nonexistent_password(sql_password_repository):
    non_existent_id = uuid4()
    with pytest.raises(PasswordNotFoundError):
        sql_password_repository.get_by_id(non_existent_id)
