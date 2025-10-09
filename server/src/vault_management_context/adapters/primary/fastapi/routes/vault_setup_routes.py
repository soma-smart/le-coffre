from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_vault_usecase,
)
from vault_management_context.application.use_cases import CreateVaultUseCase
from vault_management_context.domain.entities.share import Share
from vault_management_context.domain.exceptions import VaultManagementDomainError

router = APIRouter(prefix="/vault", tags=["Vault"])


class CreateVaultPostRequest(BaseModel):
    nb_shares: int
    threshold: int


class CreateVaultPostResponse(BaseModel):
    setup_id: str
    shares: list[Share]


@router.post(
    "/setup",
    response_model=CreateVaultPostResponse,
    status_code=201,
    summary="Create a new vault in pending state",
)
def create_vault(
    request: CreateVaultPostRequest,
    usecase: CreateVaultUseCase = Depends(get_create_vault_usecase),
):
    """
    Create a new vault with Shamir's Secret Sharing in pending state.

    - **nb_shares**: Total number of shares to generate
    - **threshold**: Minimum number of shares needed to unlock the vault
    
    Returns shares and a setup_id for validation.
    """
    try:
        result = usecase.execute(request.nb_shares, request.threshold)
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"setup_id": result.setup_id, "shares": result.shares}
