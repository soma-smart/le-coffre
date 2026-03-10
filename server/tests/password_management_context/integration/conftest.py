import pytest
from sqlmodel import Session, SQLModel, create_engine

from password_management_context.adapters.secondary.sql import (
    SqlPasswordPermissionsRepository,
    SqlPasswordRepository,
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


@pytest.fixture
def sql_password_repository(session):
    return SqlPasswordRepository(session)


@pytest.fixture
def sql_password_permissions_repository(session):
    return SqlPasswordPermissionsRepository(session)
