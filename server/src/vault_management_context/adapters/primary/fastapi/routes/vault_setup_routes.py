import logging
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


class IssuedShareLinkResponse(BaseModel):
    share_index: int
    token: str
    expires_at: datetime


class CreateVaultPostResponse(BaseModel):
    setup_id: UUID
    share_links: list[IssuedShareLinkResponse]


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

    Returns a setup_id for validation and one link token per share.
    The shares themselves are never returned: each is sealed under a key
    derived from its token, which exists only in this response. Build the link
    as `<origin>/vault-share#<token>` and hand one to each custodian. Each link
    is valid 48 hours. POST /vault/share-links/retrieve hands its share out; the
    first call opens a reopen window of 15 minutes (never past the 48 hours),
    during which the link can be retrieved again, until the custodian closes it
    with POST /vault/share-links/acknowledge. A link left unacknowledged closes
    on its own when the window ends.
    """
    try:
        setup_id = uuid4()
        command = CreateVaultCommand(nb_shares=request.nb_shares, threshold=request.threshold, setup_id=setup_id)
        result = usecase.execute(command)
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in vault setup")
        raise HTTPException(status_code=500, detail="Internal server error") from e

    return CreateVaultPostResponse(
        setup_id=setup_id,
        share_links=[
            IssuedShareLinkResponse(share_index=link.share_index, token=link.token, expires_at=link.expires_at)
            for link in result.share_links
        ],
    )
