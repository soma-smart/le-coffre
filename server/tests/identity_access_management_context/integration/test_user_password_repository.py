import pytest
from uuid import UUID, uuid4
from identity_access_management_context.domain.entities import UserPassword


@pytest.fixture
def test_save_user_password_and_get_by_id(sql_user_password_repository):
    test_user_password = UserPassword(
        id=uuid4(),
        email="test@example.com",
        password_hash=b"hashedpassword123",
        display_name="Test User",
    )
    sql_user_password_repository.save(test_user_password)
    retrieved_user_password = sql_user_password_repository.get_by_id(
        test_user_password.id
    )
    assert retrieved_user_password is not None
    assert retrieved_user_password.id == test_user_password.id
    assert retrieved_user_password.email == test_user_password.email
    assert retrieved_user_password.password_hash == test_user_password.password_hash
    assert retrieved_user_password.display_name == test_user_password.display_name


def test_get_user_password_by_email(sql_user_password_repository):
    test_user_password = UserPassword(
        id=uuid4(),
        email="test@example.com",
        password_hash=b"hashedpassword123",
        display_name="Test User",
    )
    sql_user_password_repository.save(test_user_password)
    retrieved_user_password = sql_user_password_repository.get_by_email(
        test_user_password.email
    )
    assert retrieved_user_password is not None
    assert retrieved_user_password.id == test_user_password.id
    assert retrieved_user_password.email == test_user_password.email
    assert retrieved_user_password.password_hash == test_user_password.password_hash
    assert retrieved_user_password.display_name == test_user_password.display_name


def test_get_nonexistent_user_password_by_id(sql_user_password_repository):
    non_existent_id = uuid4()
    result = sql_user_password_repository.get_by_id(non_existent_id)
    assert result is None


def test_update_user(sql_user_password_repository):
    user_password = UserPassword(
        UUID("12345678-1234-5678-1234-567812345678"),
        "toto@toto.com",
        b"hashedpassword123",
        "Toto",
    )
    sql_user_password_repository.save(user_password)

    new_password = b"newhashedpassword123"
    sql_user_password_repository.update_password(user_password.id, new_password)

    # Retrieve the updated user password
    updated_user_password = sql_user_password_repository.get_by_id(user_password.id)
    assert updated_user_password is not None
    assert updated_user_password.email == user_password.email
    assert updated_user_password.password_hash == new_password
    assert updated_user_password.display_name == user_password.display_name


def test_update_missing_user_does_nothing(sql_user_password_repository):
    sql_user_password_repository.update_password(
        UUID("12345678-1234-5678-1234-567812345678"), b"new_password_hashed"
    )
