from fastapi import Depends
from sqlmodel import Session
from starlette.requests import Request

from shared_kernel.adapters.primary.dependencies import get_session
from shared_kernel.application.gateways import DomainEventPublisher
from vault_management_context.adapters.secondary import (
    SqlVaultEventRepository,
    SqlVaultRepository,
)
from vault_management_context.application.gateways import (
    EncryptionGateway,
    ShamirGateway,
    ShareRepository,
    VaultEventRepository,
    VaultRepository,
    VaultSessionGateway,
)
from vault_management_context.application.use_cases import (
    CreateVaultUseCase,
    GetVaultStatusUseCase,
    LockVaultUseCase,
    UnlockVaultUseCase,
    ValidateVaultSetupUseCase,
)


def get_event_publisher(request: Request) -> DomainEventPublisher:
    return request.app.state.domain_event_publisher


def get_vault_event_repository(session: Session = Depends(get_session)) -> VaultEventRepository:  # noqa: B008
    return SqlVaultEventRepository(session)


def get_vault_repository(session: Session = Depends(get_session)) -> VaultRepository:  # noqa: B008
    return SqlVaultRepository(session)


def get_shamir_gateway(request: Request) -> ShamirGateway:
    return request.app.state.shamir_gateway


def get_encryption_gateway(request: Request) -> EncryptionGateway:
    return request.app.state.encryption_gateway


def get_vault_session_gateway(request: Request) -> VaultSessionGateway:
    return request.app.state.vault_session_gateway


def get_share_repository(request: Request) -> ShareRepository:
    return request.app.state.share_repository


def get_create_vault_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),  # noqa: B008
    shamir_gateway: ShamirGateway = Depends(get_shamir_gateway),  # noqa: B008
    encryption_gateway: EncryptionGateway = Depends(get_encryption_gateway),  # noqa: B008
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    vault_event_repository: VaultEventRepository = Depends(get_vault_event_repository),  # noqa: B008
):
    return CreateVaultUseCase(
        vault_repository,
        shamir_gateway,
        encryption_gateway,
        vault_session_gateway,
        event_publisher,
        vault_event_repository,
    )


def get_unlock_vault_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),  # noqa: B008
    shamir_gateway: ShamirGateway = Depends(get_shamir_gateway),  # noqa: B008
    encryption_gateway: EncryptionGateway = Depends(get_encryption_gateway),  # noqa: B008
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),  # noqa: B008
    share_repository: ShareRepository = Depends(get_share_repository),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    vault_event_repository: VaultEventRepository = Depends(get_vault_event_repository),  # noqa: B008
):
    return UnlockVaultUseCase(
        vault_repository,
        shamir_gateway,
        encryption_gateway,
        vault_session_gateway,
        share_repository,
        event_publisher,
        vault_event_repository,
    )


def get_lock_vault_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),  # noqa: B008
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),  # noqa: B008
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),  # noqa: B008
    vault_event_repository: VaultEventRepository = Depends(get_vault_event_repository),  # noqa: B008
):
    return LockVaultUseCase(vault_repository, vault_session_gateway, event_publisher, vault_event_repository)


def get_vault_status_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),  # noqa: B008
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),  # noqa: B008
    share_repository: ShareRepository = Depends(get_share_repository),  # noqa: B008
):
    return GetVaultStatusUseCase(vault_repository, vault_session_gateway, share_repository)


def get_validate_vault_setup_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),  # noqa: B008
):
    return ValidateVaultSetupUseCase(vault_repository)
