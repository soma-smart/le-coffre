import logging
import os
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlmodel import Session, create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command
from starlette.types import ASGIApp, Receive, Scope, Send

# Switch all handlers to JSON output before any logger fires.
from logging_config import configure_logging, rewire_uvicorn_logging, _trace_id_var
configure_logging()

logger = logging.getLogger(__name__)


class _NoiseFilter(logging.Filter):
    """Suppress high-frequency OK responses that would flood Loki with useless entries."""

    _SUPPRESSED_ROUTES = frozenset({"/api/health", "/api/metrics"})

    def filter(self, record: logging.LogRecord) -> bool:
        # Parse record.args directly — uvicorn access log format is a 5-tuple:
        # (client_addr, method, path, http_version, status_code)
        # Using args avoids coupling to uvicorn's internal format string.
        args = record.args
        if (
            isinstance(args, tuple)
            and len(args) == 5
            and args[1] == "GET"
            and args[2] in self._SUPPRESSED_ROUTES
            and args[4] == 200
        ):
            return False
        return True


logging.getLogger("uvicorn.access").addFilter(_NoiseFilter())


class _TraceIdMiddleware:
    """Assign a unique trace_id per request for structured log correlation.

    Reads the X-Trace-Id header if present (useful for distributed tracing),
    otherwise generates a new UUID. The trace_id is injected into every log
    record emitted during the request via _TraceIdFilter.
    Will be wired to the actual OpenTelemetry trace ID in Priority 3 (Tempo).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            trace_id = headers.get(b"x-trace-id", b"").decode() or str(uuid.uuid4())
            token = _trace_id_var.set(trace_id)
            try:
                await self.app(scope, receive, send)
            finally:
                _trace_id_var.reset(token)
        else:
            await self.app(scope, receive, send)

from config import (
    get_database_url,
    get_jwt_secret_key,
    get_jwt_algorithm,
    get_jwt_access_token_expiration_minutes,
    get_jwt_refresh_token_expiration_days,
)

from security import CsrfMiddleware, CsrfTokenManager, csrf_router
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
    InMemoryShareRepository,
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


def run_migrations(max_retries: int = 5, retry_delay: float = 5.0):
    """Run database migrations using Alembic, with retry on connection failure."""
    # Get the path to alembic.ini relative to this file
    # main.py is in server/src/, alembic.ini is in server/
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    # Escape % characters for ConfigParser interpolation
    database_url = get_database_url().replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    for attempt in range(max_retries):
        try:
            command.upgrade(alembic_cfg, "head")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(
                    "Migration attempt %d/%d failed: %s. Retrying in %.1fs...",
                    attempt + 1,
                    max_retries,
                    e,
                    retry_delay,
                )
                time.sleep(retry_delay)
            else:
                raise


def _build_engine(database_url: str):
    """Build SQLAlchemy engine with appropriate settings for the database type."""
    kwargs: dict = {"pool_pre_ping": True}
    if database_url.startswith("postgresql"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
        kwargs["connect_args"] = {"connect_timeout": 10}
    return create_engine(database_url, **kwargs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Re-apply JSON formatter to uvicorn's handlers. Uvicorn may have
    # re-initialised its logging config after our module was imported.
    rewire_uvicorn_logging()

    # Run migrations instead of create_tables
    logger.info("Starting database migrations...")
    run_migrations()
    logger.info("Database migrations completed")

    engine = _build_engine(get_database_url())

    # Create session maker for creating sessions per request
    SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    app.state.session_maker = SessionLocal

    # Stateless gateways that don't need a session
    shamir_gateway = CryptoShamirGateway()
    encryption_gateway = AesEncryptionGateway()
    vault_session_gateway = InMemoryVaultSessionGateway()
    share_repository = InMemoryShareRepository()

    app.state.shamir_gateway = shamir_gateway
    app.state.encryption_gateway = encryption_gateway
    app.state.vault_session_gateway = vault_session_gateway
    app.state.share_repository = share_repository

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

    # CSRF token manager (tokens valid for entire session)
    csrf_token_manager = CsrfTokenManager()
    app.state.csrf_token_manager = csrf_token_manager

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

    db_url = get_database_url()
    db_type = "postgresql" if db_url.startswith("postgresql") else "sqlite"
    logger.info("Application started — db=%s base_url=%s", db_type, base_url)
    yield
    logger.info("Application shutting down")


# Create the main app with lifespan
# root_path="/api" ensures OpenAPI docs are served at /api/openapi.json
app = FastAPI(lifespan=lifespan, root_path="/api")


# _TraceIdMiddleware must be outermost so trace_id is set before any other
# middleware or handler emits log records.
app.add_middleware(CsrfMiddleware)
app.add_middleware(_TraceIdMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error(
            "HTTP %d on %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Health check endpoint for Kubernetes
# Note: With root_path="/api", this will be accessible at /api/health
@app.get("/health")
async def health_check(request: Request):
    try:
        session_maker = request.app.state.session_maker
        with session_maker() as session:
            session.exec(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {e}")


# Include API routers without additional prefix
# root_path="/api" already makes all routes accessible under /api
app.include_router(csrf_router)
app.include_router(get_vault_management_router())
app.include_router(get_password_management_router())
app.include_router(get_user_management_router())
app.include_router(get_authentication_router())
app.include_router(get_group_management_router())
