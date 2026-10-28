import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_get_password_usecase,
)
from password_management_context.application.commands import GetPasswordCommand
from password_management_context.application.use_cases import GetPasswordUseCase
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordEncryptionUnavailableError,
    PasswordManagementDomainError,
    PasswordNotFoundError,
)
from shared_kernel.adapters.primary.dependencies import get_current_credential, get_current_principal
from shared_kernel.domain.entities import AuthenticatedPrincipal, PresentedCredential
from shared_kernel.domain.exceptions import AccessDeniedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class GetPasswordResponse(BaseModel):
    password: str


@router.get(
    "/{password_id}",
    response_model=GetPasswordResponse,
    status_code=200,
    summary="Get a password by ID",
    responses={
        401: {"description": "Not authenticated, or the Bearer token is invalid, revoked or regenerated"},
        404: {"description": "Unknown password, or one the caller cannot read"},
        503: {"description": "Vault is locked: an operator must unlock it, retrying will not help until then"},
    },
)
def get_password(
    password_id: UUID,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    credential: PresentedCredential | None = Depends(get_current_credential),
    usecase: GetPasswordUseCase = Depends(get_get_password_usecase),
):
    """
    Retrieve a password by its ID.

    - **password_id**: The ID of the password to retrieve
    - **Authentication**: an access_token cookie, or a bearer token. A
      read-only token, like a browser extension's, never carries the admin
      role, so it reaches only what its own user can read.

    A service account reads what its group can read, shares included until they
    expire. This is the only password route it may call.
    """
    try:
        command = GetPasswordCommand(
            requester_id=principal.principal_id,
            password_id=password_id,
            credential_id=None if credential is None else credential.credential_id,
        )
        decrypted_password = usecase.execute(command)

        return GetPasswordResponse(password=decrypted_password)
    except (PasswordNotFoundError, PasswordAccessDeniedError) as e:
        # Same status and same words for both: a different message would tell a
        # caller probing ids which ones exist.
        raise HTTPException(status_code=404, detail="Password not found") from e
    except PasswordEncryptionUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in get password")
        raise HTTPException(status_code=500, detail="Internal server error") from e
