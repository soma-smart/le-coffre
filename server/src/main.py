from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import Session, create_engine

from config import get_database_url

from vault_management_context.adapters.primary.fastapi.routes import (
    get_vault_management_router,
)
from vault_management_context.adapters.primary.private_api import EncryptionApi
from vault_management_context.adapters.secondary.gateways import (
    CryptoShamirGateway,
    AesEncryptionGateway,
    SqlVaultRepository,
    InMemoryVaultSessionGateway,
    create_tables,
)
from vault_management_context.application.use_cases import (
    EncryptUseCase,
    DecryptUseCase,
)

from password_management_context.adapters.primary.fastapi.routes import (
    get_password_management_router,
)
from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)

from rights_access_context.adapters.primary.fastapi.routes import (
    get_rights_access_router,
)
from rights_access_context.adapters.primary import AccessControllerAdapter
from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
    GrantAccessUseCase,
)
from rights_access_context.adapters.secondary import InMemoryRightsRepository

from user_management_context.adapters.output.interfaces import InMemoryUserRepository
from user_management_context.adapters.input.fastapi.routes import (
    get_user_management_router,
)

from authentication_context.adapters.primary.fastapi.routes import (
    get_authentication_router,
)
from authentication_context.adapters.secondary import (
    BcryptHashingGateway,
    InMemoryUserPasswordRepository,
    InMemorySessionRepository,
    JwtTokenGateway,
    InMemoryUserManagementGateway,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(get_database_url())
    create_tables(engine)

    with Session(engine) as session:
        # Vault management dependencies
        vault_repository = SqlVaultRepository(session)
        shamir_gateway = CryptoShamirGateway()
        encryption_gateway = AesEncryptionGateway()
        vault_session_gateway = InMemoryVaultSessionGateway()

        app.state.vault_repository = vault_repository
        app.state.shamir_gateway = shamir_gateway
        app.state.encryption_gateway = encryption_gateway
        app.state.vault_session_gateway = vault_session_gateway

        # Password management dependencies
        password_repository = InMemoryPasswordRepository()
        encrypt_use_case = EncryptUseCase(encryption_gateway, vault_session_gateway)
        decrypt_use_case = DecryptUseCase(encryption_gateway, vault_session_gateway)
        encryption_service = EncryptionApi(
            encrypt_use_case, decrypt_use_case
        )  # Expose encryption service via API

        app.state.password_repository = password_repository
        app.state.encryption_service = encryption_service

        # Rights access dependencies
        rights_repository = InMemoryRightsRepository()
        check_use_case = CheckAccessUseCase(rights_repository)
        grant_use_case = GrantAccessUseCase(rights_repository)
        access_controller = AccessControllerAdapter(check_use_case, grant_use_case)

        app.state.rights_repository = rights_repository
        app.state.access_controller = access_controller

        # User management dependencies
        user_repository = InMemoryUserRepository()

        app.state.user_repository = user_repository

        # Authentication dependencies
        user_password_repository = InMemoryUserPasswordRepository()
        password_hashing_gateway = BcryptHashingGateway()
        token_gateway = JwtTokenGateway()
        session_repository = InMemorySessionRepository()
        user_management_gateway = InMemoryUserManagementGateway()

        app.state.user_password_repository = user_password_repository
        app.state.password_hashing_gateway = password_hashing_gateway
        app.state.token_gateway = token_gateway
        app.state.session_repository = session_repository
        app.state.user_management_gateway = user_management_gateway

        yield


app = FastAPI(lifespan=lifespan, root_path="/api")
app.include_router(get_vault_management_router())
app.include_router(get_password_management_router())
app.include_router(get_rights_access_router())
app.include_router(get_user_management_router())
app.include_router(get_authentication_router())
