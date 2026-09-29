import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from shared_kernel.adapters.primary.dependencies import get_current_principal
from shared_kernel.domain.entities import ApiPrincipal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/session", tags=["Browser Extension"])


class GetExtensionSessionResponse(BaseModel):
    # The caller's own id. The extension needs it to tell which groups the
    # user actually belongs to: GET /groups returns every group on the
    # instance, so the client has to filter, exactly as the web app does.
    user_id: UUID
    email: str
    display_name: str
    is_read_only: bool


@router.get(
    "",
    status_code=200,
    response_model=GetExtensionSessionResponse,
    summary="Identify the caller behind an extension token",
)
def get_extension_session(
    principal: ApiPrincipal = Depends(get_current_principal),
):
    """
    Return who the caller is, so the extension can label its own header.

    - **Authentication**: an extension bearer token, or an access_token cookie

    Deliberately thin. The extension is not given `/users/me`: three
    bearer-reachable routes is a surface small enough to audit by eye, and this
    one answers the only question the popup actually has.
    """
    return GetExtensionSessionResponse(
        user_id=principal.user.user_id,
        email=principal.user.email,
        display_name=principal.user.display_name,
        is_read_only=principal.is_read_only,
    )
