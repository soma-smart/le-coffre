import pytest
import tempfile
import os
from pathlib import Path
from uuid import uuid4
from sqlmodel import create_engine, Session
from alembic.config import Config
from alembic import command

from identity_access_management_context.adapters.secondary.sql.sql_group_repository import (
    SqlGroupRepository,
)
from identity_access_management_context.domain.entities import PersonalGroup, Group


@pytest.fixture(scope="function")
def engine():
    """Create a temporary database engine for testing"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    try:
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})

        # Run migrations instead of create_all()
        alembic_ini_path = Path(__file__).parent.parent.parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_cfg, "head")

        yield engine
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture(scope="function")
def session(engine):
    """Create a new database session for a test"""
    with Session(engine) as session:
        yield session


@pytest.fixture
def sql_group_repository(session):
    return SqlGroupRepository(session)


def test_given_personal_group_when_saving_then_group_is_stored(sql_group_repository):
    # Given
    group_id = uuid4()
    user_id = uuid4()
    name = "testuser's Personal Group"
    personal_group = PersonalGroup(id=group_id, name=name, user_id=user_id)

    # When
    sql_group_repository.save_personal_group(personal_group)

    # Then - PersonalGroup is retrieved by user_id, not by get_by_id (which is for Group entities)
    retrieved_group = sql_group_repository.get_by_user_id(user_id)
    assert retrieved_group is not None
    assert retrieved_group.id == group_id
    assert retrieved_group.name == name
    assert retrieved_group.user_id == user_id


def test_given_personal_group_when_getting_by_user_id_then_group_is_retrieved(
    sql_group_repository,
):
    # Given
    group_id = uuid4()
    user_id = uuid4()
    name = "testuser's Personal Group"
    personal_group = PersonalGroup(id=group_id, name=name, user_id=user_id)
    sql_group_repository.save_personal_group(personal_group)

    # When
    retrieved_group = sql_group_repository.get_by_user_id(user_id)

    # Then
    assert retrieved_group is not None
    assert retrieved_group.id == group_id
    assert retrieved_group.name == name
    assert retrieved_group.user_id == user_id


def test_given_no_group_when_getting_by_user_id_then_returns_none(sql_group_repository):
    # Given
    non_existent_user_id = uuid4()

    # When
    retrieved_group = sql_group_repository.get_by_user_id(non_existent_user_id)

    # Then
    assert retrieved_group is None


def test_given_multiple_groups_when_getting_all_then_all_groups_are_retrieved(
    sql_group_repository,
):
    # Given
    group1_id = uuid4()
    user1_id = uuid4()
    group1 = PersonalGroup(
        id=group1_id, name="User1's Personal Group", user_id=user1_id
    )

    group2_id = uuid4()
    user2_id = uuid4()
    group2 = PersonalGroup(
        id=group2_id, name="User2's Personal Group", user_id=user2_id
    )

    sql_group_repository.save_personal_group(group1)
    sql_group_repository.save_personal_group(group2)

    # When
    all_groups = sql_group_repository.get_all()

    # Then
    assert len(all_groups) == 2
    assert any(g.id == group1_id for g in all_groups)
    assert any(g.id == group2_id for g in all_groups)


def test_given_no_groups_when_getting_all_then_returns_empty_list(sql_group_repository):
    # Given / When
    all_groups = sql_group_repository.get_all()

    # Then
    assert all_groups == []


# Tests for Group entity (new)
def test_given_group_when_saving_then_group_is_stored(sql_group_repository):
    # Given
    group_id = uuid4()
    name = "Development Team"
    group = Group(id=group_id, name=name, is_personal=False)

    # When
    sql_group_repository.save_group(group)

    # Then
    retrieved_group = sql_group_repository.get_by_id(group_id)
    assert retrieved_group is not None
    assert retrieved_group.id == group_id
    assert retrieved_group.name == name
    assert retrieved_group.is_personal is False


def test_given_group_when_getting_by_id_then_group_is_retrieved(sql_group_repository):
    # Given
    group_id = uuid4()
    name = "Marketing Team"
    group = Group(id=group_id, name=name, is_personal=False)
    sql_group_repository.save_group(group)

    # When
    retrieved_group = sql_group_repository.get_by_id(group_id)

    # Then
    assert retrieved_group is not None
    assert retrieved_group.id == group_id
    assert retrieved_group.name == name
    assert retrieved_group.is_personal is False


def test_given_no_group_when_getting_by_id_then_returns_none(sql_group_repository):
    # Given
    nonexistent_group_id = uuid4()

    # When
    retrieved_group = sql_group_repository.get_by_id(nonexistent_group_id)

    # Then
    assert retrieved_group is None


def test_given_personal_group_flag_when_saving_then_flag_is_preserved(
    sql_group_repository,
):
    # Given
    personal_group = Group(id=uuid4(), name="My Personal Group", is_personal=True)
    regular_group = Group(id=uuid4(), name="Regular Group", is_personal=False)

    # When
    sql_group_repository.save_group(personal_group)
    sql_group_repository.save_group(regular_group)

    # Then
    retrieved_personal = sql_group_repository.get_by_id(personal_group.id)
    retrieved_regular = sql_group_repository.get_by_id(regular_group.id)

    assert retrieved_personal.is_personal is True
    assert retrieved_regular.is_personal is False


def test_given_multiple_groups_when_saved_then_all_retrievable_by_id(
    sql_group_repository,
):
    # Given
    group1 = Group(id=uuid4(), name="Group 1", is_personal=False)
    group2 = Group(id=uuid4(), name="Group 2", is_personal=False)
    group3 = Group(id=uuid4(), name="Group 3", is_personal=True)

    # When
    sql_group_repository.save_group(group1)
    sql_group_repository.save_group(group2)
    sql_group_repository.save_group(group3)

    # Then
    retrieved1 = sql_group_repository.get_by_id(group1.id)
    retrieved2 = sql_group_repository.get_by_id(group2.id)
    retrieved3 = sql_group_repository.get_by_id(group3.id)

    assert retrieved1 is not None and retrieved1.id == group1.id
    assert retrieved2 is not None and retrieved2.id == group2.id
    assert retrieved3 is not None and retrieved3.id == group3.id
