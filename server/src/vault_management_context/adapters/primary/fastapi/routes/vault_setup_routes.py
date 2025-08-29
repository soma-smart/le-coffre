from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_vault_usecase,
)
from vault_management_context.application.use_cases import CreateVaultUseCase
from vault_management_context.domain.entities.share import Share
from vault_management_context.domain.exceptions import VaultManagementDomainError

router = APIRouter(prefix="/api/vault", tags=["Vault Setup"])


class CreateVaultPostRequest(BaseModel):
    nb_shares: int
    threshold: int


class CreateVaultPostResponse(BaseModel):
    shares: list[Share]


@router.post(
    "/setup",
    response_model=CreateVaultPostResponse,
    status_code=201,
    summary="Create a new vault",
)
def create_vault(
    request: CreateVaultPostRequest,
    usecase: CreateVaultUseCase = Depends(get_create_vault_usecase),
):
    """
    Create a new vault with Shamir's Secret Sharing.

    - **nb_shares**: Total number of shares to generate
    - **threshold**: Minimum number of shares needed to unlock the vault
    """
    try:
        shares: list[Share] = usecase.execute(request.nb_shares, request.threshold)
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"shares": shares}
