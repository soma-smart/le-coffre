from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import Session, create_engine

from config import DATABASE_URL
from vault_management_context.adapters.secondary.gateways import (
    CryptoShamirGateway,
    AesEncryptionGateway,
    SqlVaultRepository,
    InMemoryVaultSessionGateway,
    create_tables,
)
from vault_management_context.adapters.primary.fastapi.routes import (
    get_vault_management_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(DATABASE_URL)
    create_tables(engine)

    with Session(engine) as session:
        vault_repository = SqlVaultRepository(session)
        shamir_gateway = CryptoShamirGateway()
        encryption_gateway = AesEncryptionGateway()
        vault_session_gateway = InMemoryVaultSessionGateway()

        app.state.vault_repository = vault_repository
        app.state.shamir_gateway = shamir_gateway
        app.state.encryption_gateway = encryption_gateway
        app.state.vault_session_gateway = vault_session_gateway
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(get_vault_management_router())
