import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from sqlmodel import Session, create_engine
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command

from audit_logging_context.adapters.primary.all_events_subscriber import (
    AllEventsSubscriber,
)
from audit_logging_context.adapters.primary.fastapi.routes import (
    get_audit_logging_router,
)
from config import (
    get_database_url,
    get_jwt_secret_key,
    get_jwt_algorithm,
    get_jwt_access_token_expiration_minutes,
    get_jwt_refresh_token_expiration_days,
)

from shared_kernel.adapters.secondary import (
    UtcTimeGateway,
    InMemoryDomainEventPublisher,
)
from vault_management_context.adapters.primary.fastapi.routes import (
    get_vault_management_router,
)
from vault_management_context.adapters.primary.private_api import EncryptionApi
from vault_management_context.adapters.secondary import (
    CryptoShamirGateway,
    AesEncryptionGateway,
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
    PrivateApiPasswordEncryptionGateway,
)

from identity_access_management_context.adapters.secondary import (
    BcryptHashingGateway,
    JwtTokenGateway,
    OAuth2SsoGateway,
    PrivateApiSsoEncryptionGateway,
)
from identity_access_management_context.adapters.primary.fastapi.routes import (
    get_user_management_router,
    get_authentication_router,
    get_group_management_router,
)


def run_migrations():
    """Run database migrations using Alembic."""
    # Get the path to alembic.ini relative to this file
    # main.py is in server/src/, alembic.ini is in server/
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    # Escape % characters for ConfigParser interpolation
    database_url = get_database_url().replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations instead of create_tables
    run_migrations()

    engine = create_engine(get_database_url())

    # Create session maker for creating sessions per request
    SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    app.state.session_maker = SessionLocal

    # Stateless gateways that don't need a session
    shamir_gateway = CryptoShamirGateway()
    encryption_gateway = AesEncryptionGateway()
    vault_session_gateway = InMemoryVaultSessionGateway()

    app.state.shamir_gateway = shamir_gateway
    app.state.encryption_gateway = encryption_gateway
    app.state.vault_session_gateway = vault_session_gateway

    # Encryption use cases and API (stateless)
    encrypt_use_case = EncryptUseCase(encryption_gateway, vault_session_gateway)
    decrypt_use_case = DecryptUseCase(encryption_gateway, vault_session_gateway)
    encryption_api = EncryptionApi(encrypt_use_case, decrypt_use_case)
    password_encryption_gateway = PrivateApiPasswordEncryptionGateway(encryption_api)

    app.state.password_encryption_gateway = password_encryption_gateway

    # IAM dependencies (stateless)
    app.state.time_provider = UtcTimeGateway()
    # IAM uses SSO encryption gateway (same underlying API)
    sso_encryption_gateway = PrivateApiSsoEncryptionGateway(encryption_api)
    app.state.sso_encryption_gateway = sso_encryption_gateway

    password_hashing_gateway = BcryptHashingGateway()
    app.state.password_hashing_gateway = password_hashing_gateway

    token_gateway = JwtTokenGateway(
        secret_key=get_jwt_secret_key(),
        algorithm=get_jwt_algorithm(),
        access_token_expiration_minutes=get_jwt_access_token_expiration_minutes(),
        refresh_token_expiration_days=get_jwt_refresh_token_expiration_days(),
    )
    app.state.token_gateway = token_gateway

    # SSO Gateway (stateless)
    base_url = os.getenv("APP_BASE_URL", "http://localhost:8123")
    sso_gateway = OAuth2SsoGateway(
        redirect_uri=f"{base_url}/sso/callback",
        scope="openid email profile",
        provider="oauth2",
    )
    app.state.sso_gateway = sso_gateway

    # Domain event publisher (stateless)
    domain_event_publisher = InMemoryDomainEventPublisher()
    app.state.domain_event_publisher = domain_event_publisher

    # Subscribe to all events with AllEventsSubscriber that creates its own session
    domain_event_publisher.subscribe_all(AllEventsSubscriber(SessionLocal))

    yield


# Create the main app with lifespan
# root_path="/api" ensures OpenAPI docs are served at /api/openapi.json
app = FastAPI(lifespan=lifespan, root_path="/api")

# Health check endpoint for Kubernetes
# Note: With root_path="/api", this will be accessible at /api/health
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include API routers without additional prefix
# root_path="/api" already makes all routes accessible under /api
app.include_router(get_vault_management_router())
app.include_router(get_password_management_router())
app.include_router(get_user_management_router())
app.include_router(get_authentication_router())
app.include_router(get_group_management_router())
app.include_router(get_audit_logging_router())

# Mount static files for frontend if they exist
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Serve static files
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # Catch-all route for SPA (must be last)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve index.html for all non-API routes (SPA)
        return FileResponse(frontend_dist / "index.html")
