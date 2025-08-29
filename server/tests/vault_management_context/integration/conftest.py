import pytest
import tempfile
import os
from sqlmodel import create_engine, Session

from vault_management_context.adapters.secondary.gateways import (
    create_tables,
    SqlVaultRepository,
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
def vault_repository(session):
    return SqlVaultRepository(session)
