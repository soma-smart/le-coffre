from fastapi import Depends
from starlette.requests import Request
from sqlmodel import Session

from vault_management_context.application.use_cases import (
    CreateVaultUseCase,
    ValidateVaultSetupUseCase,
    UnlockVaultUseCase,
    LockVaultUseCase,
    GetVaultStatusUseCase,
)
from vault_management_context.application.gateways import (
    VaultRepository,
    ShamirGateway,
    EncryptionGateway,
    VaultSessionGateway,
    ShareRepository,
)
from vault_management_context.adapters.secondary import (
    SqlVaultRepository,
    SqlVaultEventRepository,
)
from vault_management_context.application.gateways import VaultEventRepository
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.adapters.primary.dependencies import get_session


def get_event_publisher(request: Request) -> DomainEventPublisher:
    return request.app.state.domain_event_publisher


def get_vault_event_repository(session: Session = Depends(get_session)) -> VaultEventRepository:
    return SqlVaultEventRepository(session)


def get_vault_repository(session: Session = Depends(get_session)) -> VaultRepository:
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
    vault_repository: VaultRepository = Depends(get_vault_repository),
    shamir_gateway: ShamirGateway = Depends(get_shamir_gateway),
    encryption_gateway: EncryptionGateway = Depends(get_encryption_gateway),
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    vault_event_repository: VaultEventRepository = Depends(get_vault_event_repository),
):
    return CreateVaultUseCase(
        vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway, event_publisher, vault_event_repository
    )


def get_unlock_vault_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),
    shamir_gateway: ShamirGateway = Depends(get_shamir_gateway),
    encryption_gateway: EncryptionGateway = Depends(get_encryption_gateway),
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),
    share_repository: ShareRepository = Depends(get_share_repository),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    vault_event_repository: VaultEventRepository = Depends(get_vault_event_repository),
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
    vault_repository: VaultRepository = Depends(get_vault_repository),
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),
    event_publisher: DomainEventPublisher = Depends(get_event_publisher),
    vault_event_repository: VaultEventRepository = Depends(get_vault_event_repository),
):
    return LockVaultUseCase(vault_repository, vault_session_gateway, event_publisher, vault_event_repository)


def get_vault_status_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),
    share_repository: ShareRepository = Depends(get_share_repository),
):
    return GetVaultStatusUseCase(
        vault_repository, vault_session_gateway, share_repository
    )


def get_validate_vault_setup_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),
):
    return ValidateVaultSetupUseCase(vault_repository)
