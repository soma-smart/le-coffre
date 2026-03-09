import pytest
from sqlmodel import Session, SQLModel, create_engine

from vault_management_context.adapters.secondary import (
    SqlVaultRepository,
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
def vault_repository(session):
    return SqlVaultRepository(session)
