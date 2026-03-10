import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_validate_vault_setup_usecase,
)
from vault_management_context.application.commands import ValidateVaultSetupCommand
from vault_management_context.application.use_cases import ValidateVaultSetupUseCase
from vault_management_context.domain.exceptions import VaultManagementDomainError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vault", tags=["Vault"])


class ValidateSetupRequest(BaseModel):
    setup_id: UUID


class ValidateSetupResponse(BaseModel):
    message: str


@router.post(
    "/validate-setup",
    response_model=ValidateSetupResponse,
    status_code=200,
    summary="Validate and complete vault setup",
)
def validate_vault_setup(
    request: ValidateSetupRequest,
    usecase: ValidateVaultSetupUseCase = Depends(get_validate_vault_setup_usecase),
):
    """
    Validate and complete vault setup using the setup_id from initial setup.

    - **setup_id**: The unique identifier returned from the initial setup
    """
    try:
        command = ValidateVaultSetupCommand(setup_id=str(request.setup_id))
        usecase.execute(command)
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in validate vault setup")
        raise HTTPException(status_code=500, detail="Internal server error") from e

    return {"message": "Vault setup completed successfully"}
