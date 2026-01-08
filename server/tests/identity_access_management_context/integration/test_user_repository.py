import pytest
from uuid import uuid4
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import UserNotFoundError, UserAlreadyExistsError
from identity_access_management_context.adapters.secondary.sql.sql_user_repository import SqlUserRepository

@pytest.fixture(scope="function")
def test_save_user_get_by_id(sql_user_repository):
  test_user = User(id=uuid4(), username="testuser", email="test@test.fr", name="Test User", roles=[])
  sql_user_repository.save(test_user) # Reminder: Declare the repository in conftest.py
  retrieved_user = sql_user_repository.get_by_id(test_user.id)
  assert retrieved_user is not None
  assert retrieved_user.id == test_user.id
  assert retrieved_user.username == test_user.username
  assert retrieved_user.email == test_user.email
  assert retrieved_user.name == test_user.name
  assert retrieved_user.roles == test_user.roles

def test_list_all_users(sql_user_repository):
  user1 = User(id=uuid4(), username="user1", email="test1@test.fr", name="User One", roles=[])
  user2 = User(id=uuid4(), username="user2", email="test2@test.fr", name="User Two", roles=[])
  sql_user_repository.save(user1)
  sql_user_repository.save(user2)
  users = sql_user_repository.list_all()
  assert len(users) >= 2
  user_ids = [user.id for user in users]
  assert user1.id in user_ids
  assert user2.id in user_ids

def test_delete_user(sql_user_repository):
  user_to_delete = User(id=uuid4(), username="tobedeleted", email="test@test.fr", name="To Be Deleted", roles=[])
  sql_user_repository.save(user_to_delete)
  sql_user_repository.delete(user_to_delete)
  with pytest.raises(UserNotFoundError):
    sql_user_repository.get_by_id(user_to_delete.id)

def test_delete_nonexistant_user(sql_user_repository):
  non_existent_user = User(id=uuid4(), username="nonexistent", email="test@test.fr", name="Non Existent", roles=[])
  with pytest.raises(UserNotFoundError):
    sql_user_repository.delete(non_existent_user)

def test_save_existing_user(sql_user_repository):
  existing_user = User(id=uuid4(), username="existinguser", email="test@test.fr", name="Existing User", roles=[])
  sql_user_repository.save(existing_user)
  with pytest.raises(UserAlreadyExistsError):
    sql_user_repository.save(existing_user)
    
def test_update_user(sql_user_repository):
  user_to_update = User(id=uuid4(), username="updatableuser", email="testupdate@test.fr", name="Updatable User", roles=[])
  sql_user_repository.save(user_to_update)
  user_to_update.name = "Updated User"
  sql_user_repository.update(user_to_update)
  updated_user = sql_user_repository.get_by_id(user_to_update.id)
  assert updated_user.name == "Updated User"
  
def test_update_nonexistant_user(sql_user_repository):
  non_existent_user = User(id=uuid4(), username="existinguser", email="test@test.fr", name="Existing User", roles=[])
  non_existent_user.name = "Updated non existent user"
  with pytest.raises(UserNotFoundError):
    sql_user_repository.update(non_existent_user)
