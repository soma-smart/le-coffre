import pytest
import os
import tempfile
from sqlmodel import create_engine, Session

from password_management_context.adapters.secondary.sql import (
    create_tables,
    SqlPasswordRepository,
)


@pytest.fixture(scope="function")
def database_engine():
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)  # Close the file descriptor, we just need the path

    try:
        engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        create_tables(engine)
        yield engine
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture(scope="function")
def session(database_engine):
    session = Session(database_engine)
    yield session
    session.close()


@pytest.fixture
def sql_password_repository(session):
    return SqlPasswordRepository(session)
