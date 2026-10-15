import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_acknowledge_share_link_usecase,
    get_retrieve_share_link_usecase,
)
from vault_management_context.application.commands import AcknowledgeShareLinkCommand, RetrieveShareLinkCommand
from vault_management_context.application.use_cases import AcknowledgeShareLinkUseCase, RetrieveShareLinkUseCase
from vault_management_context.domain.exceptions import (
    InvalidShareLinkLookupError,
    ShareLinkAckRejectedError,
    ShareLinkUnusableError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vault/share-links", tags=["Vault"])


class RetrieveShareLinkRequest(BaseModel):
    lookup_hash: str


class RetrieveShareLinkResponse(BaseModel):
    setup_id: str
    share_index: int
    sealed_share: str
    first_retrieved_at: datetime
    reopenable_until: datetime
    reopened: bool


class AcknowledgeShareLinkRequest(BaseModel):
    lookup_hash: str
    ack_key: str


@router.post(
    "/retrieve",
    response_model=RetrieveShareLinkResponse,
    status_code=200,
    summary="Retrieve a sealed Shamir share",
    responses={404: {"description": "The link is invalid, expired, closed or past its reopen window"}},
)
def retrieve_share_link(
    request: RetrieveShareLinkRequest,
    usecase: RetrieveShareLinkUseCase = Depends(get_retrieve_share_link_usecase),
):
    """
    Hand a custodian the share behind their link.

    - **lookup_hash**: hex SHA-256 of the link token, computed by the browser
    - **Authentication**: intentionally anonymous; custodians may have no account,
      and none exists at all when the vault is first set up.

    The token itself never reaches the server: the browser sends its hash, and
    opens the returned ciphertext with a key derived from the token, checking
    `setup_id` and `share_index` against the data it was sealed with. Works
    whether the vault is locked or not, so a custodian can still collect their
    share after a restart. A POST so link scanners cannot open the link.

    The first call starts a short window during which the link can be opened
    again (`reopened` is then true, with `first_retrieved_at`), until the
    custodian acknowledges it.
    """
    try:
        result = usecase.execute(RetrieveShareLinkCommand(lookup_hash=request.lookup_hash))
        return RetrieveShareLinkResponse(
            setup_id=result.setup_id,
            share_index=result.share_index,
            sealed_share=result.sealed_share,
            first_retrieved_at=result.first_retrieved_at,
            reopenable_until=result.reopenable_until,
            reopened=result.reopened,
        )
    except InvalidShareLinkLookupError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ShareLinkUnusableError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in retrieve share link")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/acknowledge",
    status_code=204,
    summary="Close a share link once its share is saved",
    responses={
        403: {"description": "The acknowledgement key does not come from the link's token"},
        404: {"description": "The link is invalid, not yet retrieved, or already closed"},
    },
)
def acknowledge_share_link(
    request: AcknowledgeShareLinkRequest,
    usecase: AcknowledgeShareLinkUseCase = Depends(get_acknowledge_share_link_usecase),
):
    """
    Delete a retrieved share link for good.

    - **lookup_hash**: hex SHA-256 of the link token
    - **ack_key**: hex HKDF-SHA256 of the token (info `le-coffre/vault-share-link/ack/v1`),
      which only the token holder can compute
    - **Authentication**: intentionally anonymous, like retrieval
    """
    try:
        usecase.execute(AcknowledgeShareLinkCommand(lookup_hash=request.lookup_hash, ack_key=request.ack_key))
        return Response(status_code=204)
    except InvalidShareLinkLookupError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ShareLinkAckRejectedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ShareLinkUnusableError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in acknowledge share link")
        raise HTTPException(status_code=500, detail="Internal server error") from e
