import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from sqlmodel import Session, create_engine
from alembic.config import Config
from alembic import command

from audit_logging_context.adapters.primary.all_events_subscriber import (
    AllEventsSubscriber,
)
from audit_logging_context.adapters.secondary.in_memory_event_repository import (
    InMemoryEventRepository,
)
from audit_logging_context.application.use_cases.store_event_use_case import (
    StoreEventUseCase,
)
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
from vault_management_context.adapters.secondary import (
    CryptoShamirGateway,
    AesEncryptionGateway,
    SqlVaultRepository,
    InMemoryVaultSessionGateway,
)
from vault_management_context.application.use_cases import (
    EncryptUseCase,
    DecryptUseCase,
)

from password_management_context.adapters.primary.fastapi.routes import (
    get_password_management_router,
)
from password_management_context.adapters.secondary import (
    SqlPasswordRepository,
    SqlPasswordPermissionsRepository,
)

from identity_access_management_context.adapters.secondary import (
    SqlUserRepository,
    BcryptHashingGateway,
    JwtTokenGateway,
    SqlUserPasswordRepository,
    SqlSsoUserRepository,
    SqlSsoConfigurationRepository,
    OAuth2SsoGateway,
)
from identity_access_management_context.adapters.secondary.sql import (
    SqlGroupRepository,
    SqlGroupMemberRepository,
)
from identity_access_management_context.adapters.secondary.group_access_gateway_adapter import (
    GroupAccessGatewayAdapter,
)
from identity_access_management_context.adapters.primary.fastapi.routes import (
    get_user_management_router,
    get_authentication_router,
    get_group_management_router,
)

from shared_kernel.pubsub import InMemoryDomainEventPublisher


def run_migrations():
    """Run database migrations using Alembic."""
    # Get the path to alembic.ini relative to this file
    # main.py is in server/src/, alembic.ini is in server/
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations instead of create_tables
    try:
        print("Starting migrations...")
        run_migrations()
        print("Migrations completed successfully")
    except Exception as e:
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
        # Continue anyway for now - we can fix migrations later
        pass

    print("Creating database engine...")
    engine = create_engine(get_database_url())
    print("Database engine created")

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
        password_repository = SqlPasswordRepository(session)
        password_permissions_repository = SqlPasswordPermissionsRepository(session)
        encrypt_use_case = EncryptUseCase(encryption_gateway, vault_session_gateway)
        decrypt_use_case = DecryptUseCase(encryption_gateway, vault_session_gateway)
        encryption_service = EncryptionApi(encrypt_use_case, decrypt_use_case)

        app.state.password_repository = password_repository
        app.state.password_permissions_repository = password_permissions_repository
        app.state.encryption_service = encryption_service

        # IAM dependencies
        app.state.time_provider = UtcTimeProvider()

        user_repository = SqlUserRepository(session)
        user_password_repository = SqlUserPasswordRepository(session)
        group_repository = SqlGroupRepository(session)
        group_member_repository = SqlGroupMemberRepository(session)
        group_access_gateway = GroupAccessGatewayAdapter(
            group_repository, group_member_repository
        )
        password_hashing_gateway = BcryptHashingGateway()

        app.state.user_repository = user_repository
        app.state.group_repository = group_repository
        app.state.group_member_repository = group_member_repository
        app.state.group_access_gateway = group_access_gateway

        token_gateway = JwtTokenGateway(
            secret_key=get_jwt_secret_key(),
            algorithm=get_jwt_algorithm(),
            access_token_expiration_minutes=get_jwt_access_token_expiration_minutes(),
            refresh_token_expiration_days=get_jwt_refresh_token_expiration_days(),
        )

        # SSO
        sso_configuration_repository = SqlSsoConfigurationRepository(session)
        base_url = os.getenv("APP_BASE_URL", "http://localhost:8123")
        sso_gateway = OAuth2SsoGateway(
            redirect_uri=f"{base_url}/sso/callback",
            scope="openid email profile",
            provider="oauth2",
        )
        sso_user_repository = SqlSsoUserRepository(session)

        app.state.user_password_repository = user_password_repository
        app.state.password_hashing_gateway = password_hashing_gateway
        app.state.token_gateway = token_gateway
        app.state.sso_gateway = sso_gateway
        app.state.sso_user_repository = sso_user_repository
        app.state.sso_configuration_repository = sso_configuration_repository

        app.state.event_repository = InMemoryEventRepository()

        store_event_usecase = StoreEventUseCase(app.state.event_repository)
        # Domain event publisher
        domain_event_publisher = InMemoryDomainEventPublisher()
        domain_event_publisher.subscribe_all(AllEventsSubscriber(store_event_usecase))
        app.state.domain_event_publisher = domain_event_publisher

        yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return {"status": "healthy"}


app.include_router(get_vault_management_router(), prefix="/api")
app.include_router(get_password_management_router(), prefix="/api")
app.include_router(get_user_management_router(), prefix="/api")
app.include_router(get_authentication_router(), prefix="/api")
app.include_router(get_group_management_router(), prefix="/api")

# Serve frontend static files
frontend_dist = Path("/app/frontend/dist")
if frontend_dist.exists():
    # Mount static assets with proper caching
    app.mount(
        "/assets",
        StaticFiles(directory=str(frontend_dist / "assets")),
        name="assets",
    )

    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't serve index.html for API routes
        if full_path.startswith("api/"):
            return None

        # Check if the file exists
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # For all other paths, serve index.html (SPA routing)
        return FileResponse(frontend_dist / "index.html")
