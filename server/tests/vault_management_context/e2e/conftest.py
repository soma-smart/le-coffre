import pytest
import tempfile
import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session

from vault_management_context.adapters.primary.fastapi.routes import (
    get_vault_management_router,
)
from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_vault_repository,
    get_shamir_gateway,
    get_encryption_gateway,
    get_vault_session_gateway,
)
from vault_management_context.adapters.secondary.gateways import (
    create_tables,
    SqlVaultRepository,
    CryptoShamirGateway,
    AesEncryptionGateway,
    InMemoryVaultSessionGateway,
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


@pytest.fixture
def shamir_gateway():
    return CryptoShamirGateway()


@pytest.fixture
def encryption_gateway():
    return AesEncryptionGateway()


@pytest.fixture
def vault_session_gateway():
    return InMemoryVaultSessionGateway()


@pytest.fixture
def e2e_client(
    vault_repository,
    shamir_gateway,
    encryption_gateway,
    vault_session_gateway,
):
    app = FastAPI()
    app.include_router(get_vault_management_router())

    client = TestClient(app)

    app.dependency_overrides[get_vault_repository] = lambda: vault_repository
    app.dependency_overrides[get_shamir_gateway] = lambda: shamir_gateway
    app.dependency_overrides[get_encryption_gateway] = lambda: encryption_gateway
    app.dependency_overrides[get_vault_session_gateway] = lambda: vault_session_gateway

    yield client
