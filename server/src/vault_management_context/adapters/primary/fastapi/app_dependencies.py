from fastapi import Depends
from starlette.requests import Request

from vault_management_context.application.use_cases import (
    CreateVaultUseCase,
    UnlockVaultUseCase,
    LockVaultUseCase,
    GetVaultStatusUseCase,
)
from vault_management_context.application.gateways import (
    VaultRepository,
    ShamirGateway,
    EncryptionGateway,
    VaultSessionGateway,
)


def get_vault_repository(request: Request) -> VaultRepository:
    return request.app.state.vault_repository


def get_shamir_gateway(request: Request) -> ShamirGateway:
    return request.app.state.shamir_gateway


def get_encryption_gateway(request: Request) -> EncryptionGateway:
    return request.app.state.encryption_gateway


def get_vault_session_gateway(request: Request) -> VaultSessionGateway:
    return request.app.state.vault_session_gateway


def get_create_vault_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),
    shamir_gateway: ShamirGateway = Depends(get_shamir_gateway),
    encryption_gateway: EncryptionGateway = Depends(get_encryption_gateway),
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),
):
    return CreateVaultUseCase(
        vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway
    )


def get_unlock_vault_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),
    shamir_gateway: ShamirGateway = Depends(get_shamir_gateway),
    encryption_gateway: EncryptionGateway = Depends(get_encryption_gateway),
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),
):
    return UnlockVaultUseCase(
        vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway
    )


def get_lock_vault_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),
):
    return LockVaultUseCase(vault_repository, vault_session_gateway)


def get_vault_status_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),
    vault_session_gateway: VaultSessionGateway = Depends(get_vault_session_gateway),
):
    return GetVaultStatusUseCase(vault_repository, vault_session_gateway)
