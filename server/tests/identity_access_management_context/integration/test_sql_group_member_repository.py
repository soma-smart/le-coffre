import pytest
import tempfile
import os
from pathlib import Path
from uuid import uuid4
from sqlmodel import create_engine, Session
from alembic.config import Config
from alembic import command

from identity_access_management_context.adapters.secondary.sql.sql_group_member_repository import (
    SqlGroupMemberRepository,
)


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
def sql_group_member_repository(session):
    return SqlGroupMemberRepository(session)


# Method: add_member
def test_given_valid_data_when_adding_member_then_member_is_stored(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    user_id = uuid4()

    # When
    sql_group_member_repository.add_member(group_id, user_id, is_owner=False)

    # Then
    assert sql_group_member_repository.is_member(group_id, user_id)


def test_given_owner_flag_when_adding_member_then_flag_is_preserved(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    owner_id = uuid4()
    member_id = uuid4()

    # When
    sql_group_member_repository.add_member(group_id, owner_id, is_owner=True)
    sql_group_member_repository.add_member(group_id, member_id, is_owner=False)

    # Then
    assert sql_group_member_repository.is_owner(group_id, owner_id)
    assert not sql_group_member_repository.is_owner(group_id, member_id)


def test_given_existing_member_when_adding_again_then_updates_owner_status(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    user_id = uuid4()
    sql_group_member_repository.add_member(group_id, user_id, is_owner=False)

    # When - Add same member again but as owner
    sql_group_member_repository.add_member(group_id, user_id, is_owner=True)

    # Then
    assert sql_group_member_repository.is_owner(group_id, user_id)


# Method: remove_member
def test_given_existing_member_when_removing_then_member_is_deleted(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    user_id = uuid4()
    sql_group_member_repository.add_member(group_id, user_id, is_owner=False)

    # When
    sql_group_member_repository.remove_member(group_id, user_id)

    # Then
    assert not sql_group_member_repository.is_member(group_id, user_id)


def test_given_non_existent_member_when_removing_then_no_error(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    non_existent_user_id = uuid4()

    # When / Then - Should not raise an error
    sql_group_member_repository.remove_member(group_id, non_existent_user_id)


# Method: is_member
def test_given_existing_member_when_checking_membership_then_returns_true(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    user_id = uuid4()
    sql_group_member_repository.add_member(group_id, user_id, is_owner=False)

    # When
    result = sql_group_member_repository.is_member(group_id, user_id)

    # Then
    assert result is True


def test_given_non_member_when_checking_membership_then_returns_false(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    non_member_id = uuid4()

    # When
    result = sql_group_member_repository.is_member(group_id, non_member_id)

    # Then
    assert result is False


# Method: is_owner
def test_given_owner_member_when_checking_ownership_then_returns_true(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    owner_id = uuid4()
    sql_group_member_repository.add_member(group_id, owner_id, is_owner=True)

    # When
    result = sql_group_member_repository.is_owner(group_id, owner_id)

    # Then
    assert result is True


def test_given_non_owner_member_when_checking_ownership_then_returns_false(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    member_id = uuid4()
    sql_group_member_repository.add_member(group_id, member_id, is_owner=False)

    # When
    result = sql_group_member_repository.is_owner(group_id, member_id)

    # Then
    assert result is False


def test_given_non_member_when_checking_ownership_then_returns_false(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    non_member_id = uuid4()

    # When
    result = sql_group_member_repository.is_owner(group_id, non_member_id)

    # Then
    assert result is False


# Method: get_members
def test_given_multiple_members_when_getting_members_then_all_returned(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    owner_id = uuid4()
    member1_id = uuid4()
    member2_id = uuid4()

    sql_group_member_repository.add_member(group_id, owner_id, is_owner=True)
    sql_group_member_repository.add_member(group_id, member1_id, is_owner=False)
    sql_group_member_repository.add_member(group_id, member2_id, is_owner=False)

    # When
    members = sql_group_member_repository.get_members(group_id)

    # Then
    assert len(members) == 3
    assert any(m.user_id == owner_id and m.is_owner for m in members)
    assert any(m.user_id == member1_id and not m.is_owner for m in members)
    assert any(m.user_id == member2_id and not m.is_owner for m in members)


def test_given_no_members_when_getting_members_then_empty_list(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()

    # When
    members = sql_group_member_repository.get_members(group_id)

    # Then
    assert members == []


# Method: count_owners
def test_given_multiple_owners_when_counting_then_correct_count(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    owner1_id = uuid4()
    owner2_id = uuid4()

    sql_group_member_repository.add_member(group_id, owner1_id, is_owner=True)
    sql_group_member_repository.add_member(group_id, owner2_id, is_owner=True)

    # When
    count = sql_group_member_repository.count_owners(group_id)

    # Then
    assert count == 2


def test_given_no_owners_when_counting_then_returns_zero(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()

    # When
    count = sql_group_member_repository.count_owners(group_id)

    # Then
    assert count == 0


def test_given_mix_of_owners_and_members_when_counting_then_only_counts_owners(
    sql_group_member_repository,
):
    # Given
    group_id = uuid4()
    owner1_id = uuid4()
    owner2_id = uuid4()
    member1_id = uuid4()
    member2_id = uuid4()

    sql_group_member_repository.add_member(group_id, owner1_id, is_owner=True)
    sql_group_member_repository.add_member(group_id, owner2_id, is_owner=True)
    sql_group_member_repository.add_member(group_id, member1_id, is_owner=False)
    sql_group_member_repository.add_member(group_id, member2_id, is_owner=False)

    # When
    count = sql_group_member_repository.count_owners(group_id)

    # Then
    assert count == 2
