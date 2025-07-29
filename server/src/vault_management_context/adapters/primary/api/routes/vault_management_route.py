from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.vault_management_context.adapters.primary.api.app_dependencies import (
    get_create_vault_usecase,
)
from src.vault_management_context.business_logic.use_cases.create_vault_use_case import (
    CreateVaultUseCase,
)

router = APIRouter()


class CreateVaultPostRequest(BaseModel):
    nb_shares: int
    threshold: int


class CreateVaultPostResponse(BaseModel):
    shares: list[str]


@router.post("/vault", response_model=CreateVaultPostResponse, status_code=201)
def create_vault(
    request: CreateVaultPostRequest,
    usecase: CreateVaultUseCase = Depends(get_create_vault_usecase),
):
    try:
        shares: list[str] = usecase.execute(request.nb_shares, request.threshold)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"shares": shares}
