import pytest
from sqlmodel import Session, SQLModel, create_engine

from identity_access_management_context.adapters.secondary.sql import (
    SqlGroupMemberRepository,
    SqlGroupRepository,
    SqlSsoUserRepository,
    SqlUserPasswordRepository,
    SqlUserRepository,
)


@pytest.fixture(scope="function")
def database_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def session(database_engine):
    with Session(database_engine) as session:
        yield session


@pytest.fixture(scope="function")
def sql_sso_user_repository(session):
    return SqlSsoUserRepository(session)


@pytest.fixture(scope="function")
def sql_user_password_repository(session):
    return SqlUserPasswordRepository(session)


@pytest.fixture(scope="function")
def sql_user_repository(session):
    return SqlUserRepository(session)


@pytest.fixture(scope="function")
def sql_group_member_repository(session):
    return SqlGroupMemberRepository(session)


@pytest.fixture(scope="function")
def sql_group_repository(session):
    return SqlGroupRepository(session)
