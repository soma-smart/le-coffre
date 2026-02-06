import pytest
import os
import tempfile
from pathlib import Path
from sqlmodel import create_engine, Session
from alembic.config import Config
from alembic import command

from audit_logging_context.adapters.secondary.sql import SqlEventRepository


@pytest.fixture(scope="function")
def database_engine():
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)  # Close the file descriptor, we just need the path

    try:
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})

        # Run migrations instead of create_tables
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
def session(database_engine):
    with Session(database_engine) as session:
        yield session


@pytest.fixture
def sql_event_repository(session):
    return SqlEventRepository(session)
