import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_extension_tokens_usecase,
)
from identity_access_management_context.application.commands import ListExtensionTokensCommand
from identity_access_management_context.application.use_cases import ListExtensionTokensUseCase
from identity_access_management_context.domain.exceptions import IdentityAccessManagementDomainError
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/tokens", tags=["Browser Extension"])


class ExtensionTokenItem(BaseModel):
    id: UUID
    device_name: str
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_from_ip: str | None
    is_active: bool


class ListExtensionTokensResponseModel(BaseModel):
    tokens: list[ExtensionTokenItem]


@router.get(
    "",
    status_code=200,
    response_model=ListExtensionTokensResponseModel,
    summary="List the browser extensions connected to this account",
)
def list_extension_tokens(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListExtensionTokensUseCase = Depends(get_list_extension_tokens_usecase),
):
    """
    List every browser extension ever connected to the signed in account.

    - **Authentication**: requires authentication via access_token cookie

    Revoked and expired entries are included: someone checking "did I actually disconnect
    that laptop" needs to see the answer rather than an empty list. Cookie-authenticated
    only, so an extension token cannot enumerate the account's other devices.
    """
    try:
        result = usecase.execute(ListExtensionTokensCommand(requesting_user=current_user))
        return ListExtensionTokensResponseModel(
            tokens=[
                ExtensionTokenItem(
                    id=token.id,
                    device_name=token.device_name,
                    created_at=token.created_at,
                    expires_at=token.expires_at,
                    last_used_at=token.last_used_at,
                    revoked_at=token.revoked_at,
                    created_from_ip=token.created_from_ip,
                    is_active=token.is_active,
                )
                for token in result.tokens
            ]
        )
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while listing extension tokens")
        raise HTTPException(status_code=500, detail="Internal server error") from e
