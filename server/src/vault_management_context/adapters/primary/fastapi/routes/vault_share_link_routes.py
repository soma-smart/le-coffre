import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_retrieve_share_link_usecase,
)
from vault_management_context.application.commands import RetrieveShareLinkCommand
from vault_management_context.application.use_cases import RetrieveShareLinkUseCase
from vault_management_context.domain.exceptions import (
    InvalidShareLinkLookupError,
    ShareLinkUnusableError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vault/share-links", tags=["Vault"])


class RetrieveShareLinkRequest(BaseModel):
    lookup_hash: str


class RetrieveShareLinkResponse(BaseModel):
    share_index: int
    sealed_share: str


@router.post(
    "/retrieve",
    response_model=RetrieveShareLinkResponse,
    status_code=200,
    summary="Retrieve a sealed Shamir share",
    responses={404: {"description": "The link is invalid, expired or already used"}},
)
def retrieve_share_link(
    request: RetrieveShareLinkRequest,
    usecase: RetrieveShareLinkUseCase = Depends(get_retrieve_share_link_usecase),
):
    """
    Hand a custodian the share behind their link, once.

    - **lookup_hash**: hex SHA-256 of the link token, computed by the browser
    - **Authentication**: intentionally anonymous; custodians may have no account,
      and none exists at all when the vault is first set up.

    The token itself never reaches the server: the browser sends its hash, and
    opens the returned ciphertext with a key derived from the token. Works
    whether the vault is locked or not, so a custodian can still collect their
    share after a restart. A POST so link scanners cannot burn the link.
    """
    try:
        result = usecase.execute(RetrieveShareLinkCommand(lookup_hash=request.lookup_hash))
        return RetrieveShareLinkResponse(share_index=result.share_index, sealed_share=result.sealed_share)
    except InvalidShareLinkLookupError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ShareLinkUnusableError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in retrieve share link")
        raise HTTPException(status_code=500, detail="Internal server error") from e
