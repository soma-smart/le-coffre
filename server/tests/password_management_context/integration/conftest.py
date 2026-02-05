import pytest
import os
import tempfile
from sqlmodel import create_engine, Session, SQLModel

from password_management_context.adapters.secondary.sql import (
    SqlPasswordRepository,
    SqlPasswordPermissionsRepository,
)


@pytest.fixture(scope="function")
def database_engine():
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)  # Close the file descriptor, we just need the path

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


@pytest.fixture
def sql_password_repository(session):
    return SqlPasswordRepository(session)


@pytest.fixture
def sql_password_permissions_repository(session):
    return SqlPasswordPermissionsRepository(session)
