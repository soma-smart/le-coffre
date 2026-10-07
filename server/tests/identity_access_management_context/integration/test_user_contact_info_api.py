from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from identity_access_management_context.adapters.primary.private_api import (
    UserContactInfoApi,
)
from identity_access_management_context.domain.entities import User


def _build_api(database_engine) -> UserContactInfoApi:
    session_factory = sessionmaker(bind=database_engine, class_=Session, expire_on_commit=False)
    return UserContactInfoApi(session_maker=session_factory)


def _count_sql_queries(database_engine) -> list[int]:
    """Counts real SQL statements sent to the engine. Returns a single-element list
    so the caller can read the live count as more statements execute."""
    count = [0]

    def on_execute(conn, cursor, statement, parameters, context, executemany):
        count[0] += 1

    event.listen(database_engine, "before_cursor_execute", on_execute)
    return count


def test_given_several_users_when_getting_contacts_should_use_one_query_not_one_per_user(
    database_engine, sql_user_repository
):
    # Regression: get_contacts() used to call get_by_id() in a loop — one query per
    # recipient, on every vault lock/unlock broadcast to opted-in users.
    users = [
        User(id=uuid4(), username=f"user{i}", email=f"user{i}@example.com", name=f"User {i}", roles=[])
        for i in range(5)
    ]
    for user in users:
        sql_user_repository.save(user)

    api = _build_api(database_engine)
    queries = _count_sql_queries(database_engine)
    contacts = api.get_contacts([user.id for user in users])

    assert {c.user_id for c in contacts} == {user.id for user in users}
    assert queries == [1]


def test_given_ids_should_return_contacts_in_the_given_order(database_engine, sql_user_repository):
    alice_id, bob_id, carol_id = uuid4(), uuid4(), uuid4()
    sql_user_repository.save(User(id=alice_id, username="alice", email="alice@example.com", name="Alice", roles=[]))
    sql_user_repository.save(User(id=bob_id, username="bob", email="bob@example.com", name="Bob", roles=[]))
    sql_user_repository.save(User(id=carol_id, username="carol", email="carol@example.com", name="Carol", roles=[]))

    api = _build_api(database_engine)
    contacts = api.get_contacts([carol_id, alice_id, bob_id])

    assert [c.user_id for c in contacts] == [carol_id, alice_id, bob_id]
    assert [c.display_name for c in contacts] == ["Carol", "Alice", "Bob"]


def test_given_a_deleted_user_id_should_skip_it_without_failing(database_engine, sql_user_repository):
    alice_id = uuid4()
    sql_user_repository.save(User(id=alice_id, username="alice", email="alice@example.com", name="Alice", roles=[]))

    api = _build_api(database_engine)
    contacts = api.get_contacts([alice_id, uuid4()])

    assert [c.user_id for c in contacts] == [alice_id]


def test_given_no_ids_should_return_no_contacts_without_querying(database_engine):
    api = _build_api(database_engine)
    queries = _count_sql_queries(database_engine)

    assert api.get_contacts([]) == []
    assert queries == [0]
