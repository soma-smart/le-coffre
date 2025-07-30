from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.vault_management_context.adapters.secondary.gateways import (
    FakeVaultRepository,
    CryptoShamirGateway,
)

from src.vault_management_context.adapters.primary.api.routes import (
    vault_management_route,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    vault_repository = FakeVaultRepository()
    shamir_gateway = CryptoShamirGateway()

    app.state.vault_repository = vault_repository
    app.state.shamir_gateway = shamir_gateway
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(vault_management_route.router)
