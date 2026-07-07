import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Response

from config import get_cookie_secure_setting
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

SSO_STATE_COOKIE = "sso_state"
SSO_STATE_MAX_AGE_SECONDS = 600


@router.get(
    "/sso/url",
    status_code=200,
    summary="Get SSO authorization URL",
    responses={404: {"description": "SSO not configured"}, 503: {"description": "Vault is locked"}},
)
async def get_sso_url(
    response: Response,
    usecase: GetSsoAuthorizeUrlUseCase = Depends(get_sso_url_usecase),
):
    """
    Get the SSO authorization URL.

    Generates a CSRF ``state`` bound to the caller via an httpOnly cookie,
    embeds it in the authorization URL, and returns that URL. The state is
    verified against the cookie when the provider calls back.
    """
    try:
        state = secrets.token_urlsafe(32)
        command = GetSsoAuthorizeUrlCommand(state=state)
        authorize_url = await usecase.execute(command)

        response.set_cookie(
            key=SSO_STATE_COOKIE,
            value=state,
            httponly=True,
            secure=get_cookie_secure_setting(),
            samesite="lax",  # must survive the top-level GET redirect back from the IdP
            max_age=SSO_STATE_MAX_AGE_SECONDS,
        )

        return authorize_url
    except SsoConfigurationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SsoEncryptionUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in get SSO URL")
        raise HTTPException(status_code=500, detail="Internal server error") from e
