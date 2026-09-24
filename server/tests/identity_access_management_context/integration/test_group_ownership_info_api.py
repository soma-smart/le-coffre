from uuid import uuid4

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from identity_access_management_context.adapters.primary.private_api import (
    GroupOwnershipInfoApi,
)
from identity_access_management_context.domain.entities import Group, User


def _build_api(database_engine) -> GroupOwnershipInfoApi:
    session_factory = sessionmaker(bind=database_engine, class_=Session, expire_on_commit=False)
    return GroupOwnershipInfoApi(session_maker=session_factory)


def test_given_existing_owner_when_getting_owner_info_should_return_details(
    database_engine, sql_user_repository, sql_group_repository, sql_group_member_repository
):
    user_id = uuid4()
    group_id = uuid4()
    sql_user_repository.save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))
    sql_group_repository.save_group(Group(id=group_id, name="Development Team", is_personal=False))
    sql_group_member_repository.add_member(group_id, user_id, is_owner=True)

    api = _build_api(database_engine)
    info = api.get_owner_info(user_id, group_id)

    assert info is not None
    assert info.email == "alice@example.com"
    assert info.display_name == "Alice"
    assert info.group_name == "Development Team"


def test_given_nonexistent_user_when_getting_owner_info_should_return_none(database_engine, sql_group_repository):
    group_id = uuid4()
    sql_group_repository.save_group(Group(id=group_id, name="Development Team", is_personal=False))

    api = _build_api(database_engine)
    info = api.get_owner_info(uuid4(), group_id)

    assert info is None


def test_given_nonexistent_group_when_getting_owner_info_should_return_none(database_engine, sql_user_repository):
    user_id = uuid4()
    sql_user_repository.save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))

    api = _build_api(database_engine)
    info = api.get_owner_info(user_id, uuid4())

    assert info is None


def test_given_user_and_group_exist_but_user_is_not_an_owner_when_getting_owner_info_should_return_none(
    database_engine, sql_user_repository, sql_group_repository
):
    """A (user_id, group_id) pair with no ownership relationship must not be presented as owner info."""
    user_id = uuid4()
    group_id = uuid4()
    sql_user_repository.save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))
    sql_group_repository.save_group(Group(id=group_id, name="Development Team", is_personal=False))

    api = _build_api(database_engine)
    info = api.get_owner_info(user_id, group_id)

    assert info is None


def test_given_user_is_member_but_not_owner_when_getting_owner_info_should_return_none(
    database_engine, sql_user_repository, sql_group_repository, sql_group_member_repository
):
    user_id = uuid4()
    group_id = uuid4()
    sql_user_repository.save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))
    sql_group_repository.save_group(Group(id=group_id, name="Development Team", is_personal=False))
    sql_group_member_repository.add_member(group_id, user_id, is_owner=False)

    api = _build_api(database_engine)
    info = api.get_owner_info(user_id, group_id)

    assert info is None
