import logging

from fastapi import APIRouter, Depends, HTTPException

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_sso_url_usecase,
)
from identity_access_management_context.application.commands import GetSsoAuthorizeUrlCommand
from identity_access_management_context.application.use_cases import GetSsoAuthorizeUrlUseCase
from identity_access_management_context.domain.exceptions import (
    IdentityAccessManagementDomainError,
    SsoConfigurationNotFoundError,
    SsoEncryptionUnavailableError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/sso/url",
    status_code=200,
    summary="Get SSO authorization URL",
    responses={404: {"description": "SSO not configured"}, 503: {"description": "Vault is locked"}},
)
async def get_sso_url(
    usecase: GetSsoAuthorizeUrlUseCase = Depends(get_sso_url_usecase),
):
    """
    Get the SSO authorization URL.

    Returns the SSO authorization URL.
    """
    try:
        command = GetSsoAuthorizeUrlCommand()
        return await usecase.execute(command)
    except SsoConfigurationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SsoEncryptionUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in get SSO URL")
        raise HTTPException(status_code=500, detail="Internal server error") from e
