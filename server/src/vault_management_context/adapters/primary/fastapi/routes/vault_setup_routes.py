from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging
from uuid import UUID, uuid4

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_vault_usecase,
)
from vault_management_context.application.commands import CreateVaultCommand
from vault_management_context.application.use_cases import CreateVaultUseCase
from vault_management_context.domain.exceptions import VaultManagementDomainError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vault", tags=["Vault"])


class CreateVaultPostRequest(BaseModel):
    nb_shares: int
    threshold: int


class ShareResponse(BaseModel):
    secret: str


class CreateVaultPostResponse(BaseModel):
    setup_id: UUID
    shares: list[ShareResponse]


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
        setup_id = uuid4()
        command = CreateVaultCommand(
            nb_shares=request.nb_shares, threshold=request.threshold, setup_id=setup_id
        )
        result = usecase.execute(command)
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in vault setup")
        raise HTTPException(status_code=500, detail="Internal server error")

    shares_response = [{"secret": share.secret} for share in result.shares]
    return {"setup_id": setup_id, "shares": shares_response}
