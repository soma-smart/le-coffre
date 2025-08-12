from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from vault_management_context.adapters.primary.api.app_dependencies import (
    get_create_vault_usecase,
    get_vault_status_usecase,
)
from vault_management_context.application.use_cases import (
    CreateVaultUseCase,
    GetVaultStatusUseCase,
)
from vault_management_context.domain.entities.share import Share
from vault_management_context.domain.exceptions import VaultManagementDomainError

router = APIRouter(prefix="/api/vault")


class CreateVaultPostRequest(BaseModel):
    nb_shares: int
    threshold: int


class CreateVaultPostResponse(BaseModel):
    shares: list[Share]


@router.post("/setup", response_model=CreateVaultPostResponse, status_code=201)
def create_vault(
    request: CreateVaultPostRequest,
    usecase: CreateVaultUseCase = Depends(get_create_vault_usecase),
):
    try:
        shares: list[Share] = usecase.execute(request.nb_shares, request.threshold)
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"shares": shares}


@router.head("", status_code=200)
def get_vault_status(
    usecase: GetVaultStatusUseCase = Depends(get_vault_status_usecase),
):
    if not usecase.execute():
        raise HTTPException(status_code=404, detail="Vault not found")
