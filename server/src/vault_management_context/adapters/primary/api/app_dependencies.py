from fastapi import Depends
from starlette.requests import Request

from vault_management_context.application.use_cases import CreateVaultUseCase
from vault_management_context.application.gateways import (
    VaultRepository,
    ShamirGateway,
)


def get_vault_repository(request: Request) -> VaultRepository:
    return request.app.state.vault_repository


def get_shamir_gateway(request: Request) -> ShamirGateway:
    return request.app.state.shamir_gateway


def get_create_vault_usecase(
    vault_repository: VaultRepository = Depends(get_vault_repository),
    shamir_gateway: ShamirGateway = Depends(get_shamir_gateway),
):
    return CreateVaultUseCase(vault_repository, shamir_gateway)
