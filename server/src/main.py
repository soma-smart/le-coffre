from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import Session, create_engine
import os

from config import (
    get_database_url,
    get_jwt_secret_key,
    get_jwt_algorithm,
    get_jwt_access_token_expiration_minutes,
    get_jwt_refresh_token_expiration_days,
)

from shared_kernel.time import UtcTimeProvider
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

from rights_access_context.adapters.primary import AccessControllerAdapter
from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
    GetOwnerAccessUseCase,
    SetOwnerAccessUseCase,
)
from rights_access_context.adapters.secondary import InMemoryRightsRepository

from identity_access_management_context.adapters.secondary import (
    InMemoryUserRepository,
    BcryptHashingGateway,
    InMemoryUserPasswordRepository,
    InMemorySessionRepository,
    JwtTokenGateway,
    UserManagementGatewayAdapter,
    OAuth2SsoGateway,
    InMemorySsoUserRepository,
)
from identity_access_management_context.adapters.primary.fastapi.routes import (
    get_user_management_router,
    get_authentication_router,
)
from identity_access_management_context.application.use_cases import (
    CreateUserUseCase,
    CanCreateAdminUseCase,
)

from shared_kernel.pubsub import InMemoryDomainEventPublisher


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
        set_owner_use_case = SetOwnerAccessUseCase(rights_repository)
        get_owner_use_case = GetOwnerAccessUseCase(rights_repository)
        access_controller = AccessControllerAdapter(
            check_use_case, set_owner_use_case, get_owner_use_case
        )

        app.state.rights_repository = rights_repository
        app.state.access_controller = access_controller

        # IAM dependencies
        app.state.time_provider = UtcTimeProvider()

        user_repository = InMemoryUserRepository()
        create_user_usecase = CreateUserUseCase(user_repository)
        can_create_admin_usecase = CanCreateAdminUseCase(user_repository)

        app.state.user_repository = user_repository

        user_password_repository = InMemoryUserPasswordRepository()
        password_hashing_gateway = BcryptHashingGateway()
        token_gateway = JwtTokenGateway(
            secret_key=get_jwt_secret_key(),
            algorithm=get_jwt_algorithm(),
            access_token_expiration_minutes=get_jwt_access_token_expiration_minutes(),
            refresh_token_expiration_days=get_jwt_refresh_token_expiration_days(),
        )
        session_repository = InMemorySessionRepository()
        user_management_gateway = UserManagementGatewayAdapter(
            create_user_usecase, can_create_admin_usecase
        )

        # SSO Gateway with OAuth2/OIDC support
        # Base URL should be the public URL of your application
        base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        sso_gateway = OAuth2SsoGateway(
            base_url=base_url,
            redirect_uri=f"{base_url}/api/auth/sso/callback",
            scope="openid email profile",
            provider="oauth2",
        )
        sso_user_repository = InMemorySsoUserRepository()

        app.state.user_password_repository = user_password_repository
        app.state.password_hashing_gateway = password_hashing_gateway
        app.state.token_gateway = token_gateway
        app.state.session_repository = session_repository
        app.state.user_management_gateway = user_management_gateway
        app.state.sso_gateway = sso_gateway
        app.state.sso_user_repository = sso_user_repository

        # Domain event publisher
        domain_event_publisher = InMemoryDomainEventPublisher()
        app.state.domain_event_publisher = domain_event_publisher

        yield


app = FastAPI(lifespan=lifespan, root_path="/api")
app.include_router(get_vault_management_router())
app.include_router(get_password_management_router())
app.include_router(get_user_management_router())
app.include_router(get_authentication_router())
