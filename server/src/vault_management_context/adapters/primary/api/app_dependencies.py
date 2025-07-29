from fastapi import Depends
from starlette.requests import Request

from src.vault_management_context.business_logic.use_cases.create_vault_use_case import (
    CreateVaultUseCase,
)
from src.vault_management_context.business_logic.gateways.vault_repository import (
    VaultRepository,
)
from src.vault_management_context.business_logic.gateways.shamir_gateway import (
    ShamirGateway,
)


def get_vault_repository(request: Request) -> VaultRepository:
    return request.app.state.vault_repository


def get_shamir_gateway(request: Request) -> ShamirGateway:
    return request.app.state.shamir_gateway


def get_create_vault_usecase(
    vault_repository=Depends(get_vault_repository),
    shamir_gateway=Depends(get_shamir_gateway),
):
    return CreateVaultUseCase(vault_repository, shamir_gateway)
