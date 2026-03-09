import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_share_repository,
)
from vault_management_context.application.commands import ClearPendingSharesCommand
from vault_management_context.application.gateways import ShareRepository
from vault_management_context.application.use_cases.clear_pending_shares_use_case import (
    ClearPendingSharesUseCase,
)

router = APIRouter(prefix="/vault/unlock", tags=["Vault"])


class ClearPendingSharesResponse(BaseModel):
    message: str


def get_clear_pending_shares_usecase(
    share_repository: ShareRepository = Depends(get_share_repository),  # noqa: B008
) -> ClearPendingSharesUseCase:
    return ClearPendingSharesUseCase(share_repository=share_repository)


@router.delete(
    "/clear",
    response_model=ClearPendingSharesResponse,
    status_code=200,
    summary="Clear all pending shares",
)
def clear_pending_shares(
    usecase: ClearPendingSharesUseCase = Depends(get_clear_pending_shares_usecase),  # noqa: B008
):
    """
    Clear all pending shares that were submitted but didn't unlock the vault.

    This endpoint allows users to reset the unlock process by removing all
    previously submitted shares. Useful when shares are stale or incorrect.

    This endpoint does not require authentication as it's part of the unlock flow.
    """
    try:
        command = ClearPendingSharesCommand()
        usecase.execute(command)
        return {"message": "Pending shares cleared successfully"}
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
