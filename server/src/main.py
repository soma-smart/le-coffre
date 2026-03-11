import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_delay,
    wait_exponential_jitter,
)

from alembic import command
from config import (
    get_database_url,
    get_jwt_access_token_expiration_minutes,
    get_jwt_algorithm,
    get_jwt_refresh_token_expiration_days,
    get_jwt_secret_key,
    get_rate_limit_api_max_requests,
    get_rate_limit_auth_max_requests,
    get_rate_limit_enabled,
    get_rate_limit_window_seconds,
)
from identity_access_management_context.adapters.primary.fastapi.routes import (
    get_authentication_router,
    get_group_management_router,
    get_user_management_router,
)
from identity_access_management_context.adapters.secondary import (
    BcryptHashingGateway,
    JwtTokenGateway,
    OAuth2SsoGateway,
    PrivateApiSsoEncryptionGateway,
)
from monitoring import setup_logging, setup_monitoring
from password_management_context.adapters.primary.fastapi.routes import (
    get_password_management_router,
)
from password_management_context.adapters.secondary import (
    PrivateApiPasswordEncryptionGateway,
)
from security import (
    CsrfMiddleware,
    CsrfTokenManager,
    InMemoryRateLimiter,
    RateLimitMiddleware,
    csrf_router,
)
from shared_kernel.adapters.primary.request_id_middleware import (
    RequestIdFilter,
    RequestIdMiddleware,
)
from shared_kernel.adapters.secondary import (
    InMemoryDomainEventPublisher,
    UtcTimeGateway,
)
from vault_management_context.adapters.primary.fastapi.routes import (
    get_vault_management_router,
)
from vault_management_context.adapters.primary.private_api import EncryptionApi
from vault_management_context.adapters.secondary import (
    AesEncryptionGateway,
    CryptoShamirGateway,
    InMemoryShareRepository,
    InMemoryVaultSessionGateway,
)
from vault_management_context.application.use_cases import (
    DecryptUseCase,
    EncryptUseCase,
)

setup_logging()
logging.getLogger().addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Run Alembic migrations with exponential backoff retry on transient DB errors."""
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    database_url = get_database_url().replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    _run_migrations_with_retry(alembic_cfg)


@retry(
    wait=wait_exponential_jitter(initial=2, max=60),
    retry=retry_if_exception_type(SQLAlchemyOperationalError),
    stop=stop_after_delay(600),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _run_migrations_with_retry(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")


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
    app.state.ready = False
    app.state.migration_failed = False

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

    # Rate limiter (in-memory sliding window)
    rate_limiter = InMemoryRateLimiter()
    app.state.rate_limiter = rate_limiter
    app.state.rate_limit_auth_max_requests = get_rate_limit_auth_max_requests()
    app.state.rate_limit_api_max_requests = get_rate_limit_api_max_requests()
    app.state.rate_limit_window_seconds = get_rate_limit_window_seconds()

    db_url = get_database_url()
    db_type = "postgresql" if db_url.startswith("postgresql") else "sqlite"

    async def _run_migrations_in_background():
        try:
            logger.info("Starting database migrations...")
            await asyncio.to_thread(run_migrations)
            app.state.ready = True
            logger.info("Database migrations completed — application is ready")
        except Exception:
            app.state.migration_failed = True
            logger.critical(
                "Database migrations failed after all retries — liveness probe will fail to trigger a restart",
                exc_info=True,
            )

    migration_task = asyncio.create_task(_run_migrations_in_background())
    logger.info("Application started — db=%s base_url=%s", db_type, base_url)
    yield
    migration_task.cancel()
    logger.info("Application shutting down")
    # Flush and shut down OTel providers to avoid losing buffered spans/metrics/logs
    if _otel_providers is not None:
        tracer_provider, meter_provider, logger_provider = _otel_providers
        tracer_provider.force_flush()
        tracer_provider.shutdown()
        meter_provider.force_flush()
        meter_provider.shutdown()
        logger_provider.force_flush()
        logger_provider.shutdown()


# Create the main app with lifespan
# root_path="/api" ensures OpenAPI docs are served at /api/openapi.json
app = FastAPI(lifespan=lifespan, root_path="/api")


# Add CSRF protection middleware
app.add_middleware(CsrfMiddleware)
app.add_middleware(RequestIdMiddleware)

# Add rate limiting middleware (runs before CSRF since middlewares execute in reverse order)
if get_rate_limit_enabled():
    app.add_middleware(RateLimitMiddleware)
_otel_providers = setup_monitoring(app)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
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


# Liveness probe: process is alive and event loop is responsive.
# Fails only if migrations have fatally failed, to trigger a Kubernetes restart.
# Note: With root_path="/api", this will be accessible at /api/health
@app.get("/health")
async def health_check(request: Request):
    if getattr(request.app.state, "migration_failed", False):
        raise HTTPException(status_code=503, detail="Migrations failed")
    return {"status": "healthy"}


# Readiness probe: process is ready to serve traffic (migrations done + DB reachable)
# Note: With root_path="/api", this will be accessible at /api/health/ready
@app.get("/health/ready")
async def readiness_check(request: Request):
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Migrations in progress")
    try:
        session_maker = request.app.state.session_maker
        with session_maker() as session:
            session.exec(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {e}") from e


# Include API routers without additional prefix
# root_path="/api" already makes all routes accessible under /api
app.include_router(csrf_router)
app.include_router(get_vault_management_router())
app.include_router(get_password_management_router())
app.include_router(get_user_management_router())
app.include_router(get_authentication_router())
app.include_router(get_group_management_router())
