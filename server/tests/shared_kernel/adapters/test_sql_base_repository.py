"""Tests for SQLBaseRepository transaction management."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, create_engine, select

from shared_kernel.adapters.secondary.sql import SQLBaseRepository


# Model for testing
class UserModel(SQLModel, table=True):
    __tablename__ = "test_users"

    id: str = Field(primary_key=True)
    email: str = Field(unique=True)
    name: str


# Repository for testing
class UserRepository(SQLBaseRepository):
    def save_with_commit(self, user: UserModel) -> None:
        """Save user using commit() method."""
        self._session.add(user)
        self.commit()

    def save_with_commit_and_refresh(self, user: UserModel) -> None:
        """Save user using commit_and_refresh() method."""
        self._session.add(user)
        self.commit_and_refresh(user)

    def get_by_email(self, email: str) -> UserModel | None:
        """Read-only operation - no commit needed."""
        statement = select(UserModel).where(UserModel.email == email)
        return self._session.exec(statement).first()


@pytest.fixture(scope="function")
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def session(engine):
    """Create session with context manager for test isolation."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def repository(session):
    """Create test repository."""
    return UserRepository(session)


def test_commit_method_succeeds_on_valid_data(repository):
    """Test that commit() successfully commits valid data."""
    user = UserModel(id=str(uuid4()), email="test@example.com", name="Test User")

    repository.save_with_commit(user)

    # Verify saved
    retrieved = repository.get_by_email("test@example.com")
    assert retrieved is not None
    assert retrieved.name == "Test User"


def test_commit_method_rolls_back_on_error(repository):
    """Test that commit() automatically rolls back on IntegrityError."""
    user1 = UserModel(id=str(uuid4()), email="duplicate@example.com", name="User 1")
    user2 = UserModel(id=str(uuid4()), email="duplicate@example.com", name="User 2")

    # First save succeeds
    repository.save_with_commit(user1)

    # Second save with duplicate email should fail and rollback
    with pytest.raises(IntegrityError):
        repository.save_with_commit(user2)

    # Session should still be usable after rollback
    user3 = UserModel(id=str(uuid4()), email="valid@example.com", name="User 3")
    repository.save_with_commit(user3)

    retrieved = repository.get_by_email("valid@example.com")
    assert retrieved is not None


def test_commit_and_refresh_method_succeeds(repository):
    """Test that commit_and_refresh() commits and refreshes object."""
    user = UserModel(id=str(uuid4()), email="refresh@example.com", name="Refresh User")

    repository.save_with_commit_and_refresh(user)

    # Object should be refreshed with database values
    assert user.email == "refresh@example.com"
    assert user.name == "Refresh User"


def test_commit_and_refresh_rolls_back_on_error(repository):
    """Test that commit_and_refresh() rolls back on error."""
    user1 = UserModel(id=str(uuid4()), email="dup@example.com", name="User 1")
    user2 = UserModel(id=str(uuid4()), email="dup@example.com", name="User 2")

    repository.save_with_commit_and_refresh(user1)

    with pytest.raises(IntegrityError):
        repository.save_with_commit_and_refresh(user2)

    # Session should still work
    user3 = UserModel(id=str(uuid4()), email="ok@example.com", name="User 3")
    repository.save_with_commit_and_refresh(user3)
    assert repository.get_by_email("ok@example.com") is not None


def test_multiple_operations_in_sequence_after_error(repository):
    """Test that multiple operations work after an error is handled."""
    # First operation succeeds
    user1 = UserModel(id=str(uuid4()), email="seq1@example.com", name="User 1")
    repository.save_with_commit(user1)

    # Second operation fails
    user2 = UserModel(id=str(uuid4()), email="seq1@example.com", name="Duplicate")
    with pytest.raises(IntegrityError):
        repository.save_with_commit(user2)

    # Third operation succeeds (proves rollback worked)
    user3 = UserModel(id=str(uuid4()), email="seq3@example.com", name="User 3")
    repository.save_with_commit(user3)

    # Verify all valid users were saved
    assert repository.get_by_email("seq1@example.com") is not None
    assert repository.get_by_email("seq3@example.com") is not None
