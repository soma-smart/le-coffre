import os
from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import Session, create_engine
from alembic.config import Config
from alembic import command

from audit_logging_context.adapters.primary.all_events_subscriber import (
    AllEventsSubscriber,
)
from audit_logging_context.adapters.secondary.sql import SqlEventRepository
from audit_logging_context.application.use_cases.store_event_use_case import (
    StoreEventUseCase,
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
    PrivateApiPasswordEncryptionGateway,
)

from identity_access_management_context.adapters.secondary import (
    SqlUserRepository,
    BcryptHashingGateway,
    JwtTokenGateway,
    SqlUserPasswordRepository,
    SqlSsoUserRepository,
    SqlSsoConfigurationRepository,
    OAuth2SsoGateway,
    PrivateApiSsoEncryptionGateway,
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
    run_migrations()

    engine = create_engine(get_database_url())

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
        encryption_api = EncryptionApi(encrypt_use_case, decrypt_use_case)
        password_encryption_gateway = PrivateApiPasswordEncryptionGateway(
            encryption_api
        )

        app.state.password_repository = password_repository
        app.state.password_permissions_repository = password_permissions_repository
        app.state.password_encryption_gateway = password_encryption_gateway

        # IAM dependencies
        app.state.time_provider = UtcTimeGateway()
        # IAM uses SSO encryption gateway (same underlying API)
        sso_encryption_gateway = PrivateApiSsoEncryptionGateway(encryption_api)
        app.state.sso_encryption_gateway = sso_encryption_gateway

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

        app.state.event_repository = SqlEventRepository(session)

        store_event_usecase = StoreEventUseCase(app.state.event_repository)
        # Domain event publisher
        domain_event_publisher = InMemoryDomainEventPublisher()
        domain_event_publisher.subscribe_all(AllEventsSubscriber(store_event_usecase))
        app.state.domain_event_publisher = domain_event_publisher

        yield


app = FastAPI(lifespan=lifespan, root_path="/api")
app.include_router(get_vault_management_router())
app.include_router(get_password_management_router())
app.include_router(get_user_management_router())
app.include_router(get_authentication_router())
app.include_router(get_group_management_router())
app.include_router(get_audit_logging_router())
