import pytest
from uuid import uuid4
from identity_access_management_context.domain.entities import UserPassword
from identity_access_management_context.adapters.secondary.sql.sql_user_password_repository import SqlUserPasswordRepository
from identity_access_management_context.domain.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError
)

@pytest.fixture
def test_save_user_password_and_get_by_id(sql_user_password_repository):
    test_user_password = UserPassword(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashedpassword123",
        display_name="Test User"
    )
    sql_user_password_repository.save(test_user_password)
    retrieved_user_password = sql_user_password_repository.get_by_id(test_user_password.id)
    assert retrieved_user_password is not None
    assert retrieved_user_password.id == test_user_password.id
    assert retrieved_user_password.email == test_user_password.email
    assert retrieved_user_password.password_hash == test_user_password.password_hash
    assert retrieved_user_password.display_name == test_user_password.display_name


def test_get_user_password_by_email(sql_user_password_repository):
    test_user_password = UserPassword(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashedpassword123",
        display_name="Test User"
    )
    sql_user_password_repository.save(test_user_password)
    retrieved_user_password = sql_user_password_repository.get_by_email(test_user_password.email)
    assert retrieved_user_password is not None
    assert retrieved_user_password.id == test_user_password.id
    assert retrieved_user_password.email == test_user_password.email
    assert retrieved_user_password.password_hash == test_user_password.password_hash
    assert retrieved_user_password.display_name == test_user_password.display_name

def test_get_nonexistent_user_password_by_id(sql_user_password_repository):
    non_existent_id = uuid4()
    result = sql_user_password_repository.get_by_id(non_existent_id)
    assert result is None
