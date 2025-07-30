from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.vault_management_context.adapters.primary.api.app_dependencies import (
    get_create_vault_usecase,
    get_vault_status_usecase,
)
from src.vault_management_context.application.use_cases import (
    CreateVaultUseCase,
    GetVaultStatusUseCase,
)

router = APIRouter(prefix="/api/vault")


class CreateVaultPostRequest(BaseModel):
    nb_shares: int
    threshold: int


class CreateVaultPostResponse(BaseModel):
    shares: list[str]


@router.post("/setup", response_model=CreateVaultPostResponse, status_code=201)
def create_vault(
    request: CreateVaultPostRequest,
    usecase: CreateVaultUseCase = Depends(get_create_vault_usecase),
):
    try:
        shares: list[str] = usecase.execute(request.nb_shares, request.threshold)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"shares": shares}


@router.head("", status_code=200)
def get_vault_status(
    usecase: GetVaultStatusUseCase = Depends(get_vault_status_usecase),
):
    if not usecase.execute():
        raise HTTPException(status_code=404, detail="Vault not found")
