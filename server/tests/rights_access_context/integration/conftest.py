import os
import tempfile

import pytest
from rights_access_context.adapters.secondary.sql.model.rights_model import (
    OwnershipsTable,
    PermissionsTable,
)
from rights_access_context.adapters.secondary.sql.sql_rights_repository import (
    SqlRightsRepository,
)
from sqlmodel import Session, create_engine


@pytest.fixture(scope="function")
def database_engine_rights():
    """Create a temporary database engine for rights tables"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    try:
        engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        # Create both tables
        PermissionsTable.metadata.create_all(engine)
        OwnershipsTable.metadata.create_all(engine)
        yield engine
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture(scope="function")
def session(database_engine_rights):
    """Create a database session for testing"""
    session = Session(database_engine_rights)
    yield session
    session.close()


@pytest.fixture(scope="function")
def sql_rights_repository(session):
    """Create a SqlRightsRepository instance"""
    return SqlRightsRepository(session)
