import pytest
from uuid import uuid4, UUID
from password_management_context.domain.entities import Password

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
    assert sql_password_repository.get_by_id(password_id) is None
