import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import get_get_user_usecase
from identity_access_management_context.application.commands import GetUserCommand
from identity_access_management_context.application.use_cases import GetUserUseCase
from identity_access_management_context.domain.exceptions import UserNotFoundError
from shared_kernel.adapters.primary.dependencies import get_current_credential, get_current_principal
from shared_kernel.domain.entities import AuthenticatedPrincipal, PresentedCredential

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
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    credential: PresentedCredential | None = Depends(get_current_credential),
    usecase: GetUserUseCase = Depends(get_get_user_usecase),
):
    """
    Return who the caller is, so the extension can label its own header.

    - **Authentication**: a bearer token, or an access_token cookie

    Deliberately thin. The extension is not given `/users/me`: three
    bearer-reachable routes is a surface small enough to audit by eye, and this
    one answers the only question the popup actually has.
    """
    if principal.kind != "user":
        raise HTTPException(status_code=403, detail="Only a user may call this route")
    try:
        user = usecase.execute(GetUserCommand(user_id=principal.principal_id))
    except UserNotFoundError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e
    return GetExtensionSessionResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.name,
        is_read_only=credential is not None and credential.read_only,
    )
