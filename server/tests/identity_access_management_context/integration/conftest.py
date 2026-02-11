import pytest
import tempfile
import os
from sqlmodel import create_engine, Session, SQLModel
from identity_access_management_context.adapters.secondary.sql import (
    SqlSsoUserRepository,
    SqlUserRepository,
    SqlUserPasswordRepository,
    SqlGroupMemberRepository,
    SqlGroupRepository,
)


@pytest.fixture(scope="function")
def database_engine():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    try:
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})

        # Create all tables
        SQLModel.metadata.create_all(engine)

        yield engine
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


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
