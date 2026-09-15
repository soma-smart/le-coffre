import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel

from config import (
    get_cookie_secure_setting,
    get_jwt_access_token_expiration_seconds,
    get_jwt_refresh_token_expiration_seconds,
)
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_sso_login_usecase,
)
from identity_access_management_context.adapters.primary.fastapi.routes.sso.get_sso_url_route import (
    SSO_STATE_COOKIE,
)
from identity_access_management_context.application.commands.sso_login_command import (
    SsoLoginCommand,
)
from identity_access_management_context.application.use_cases import SsoLoginUseCase
from identity_access_management_context.domain.exceptions import (
    IdentityAccessManagementDomainError,
    InvalidSsoCodeException,
    SsoEncryptionUnavailableError,
)
from shared_kernel.adapters.primary.cookie_revocation import revoke_cookie

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _revoke_sso_state(request: Request, response: Response) -> None:
    revoke_cookie(request, response, SSO_STATE_COOKIE, secure=get_cookie_secure_setting(), samesite="lax")


def _state_rejection_reason(state: str | None, expected_state: str | None) -> str | None:
    """Why the CSRF state check failed, or None when it passed."""
    if not state:
        return "state query parameter missing"
    if not expected_state:
        return "sso_state cookie missing — the client must reuse one cookie jar across /auth/sso/url and this callback"
    if not secrets.compare_digest(state, expected_state):
        return "state mismatch"
    return None


class SsoUserInfo(BaseModel):
    user_id: UUID
    email: str
    display_name: str
    is_new_user: bool


class SsoCallbackResponse(BaseModel):
    message: str
    user: SsoUserInfo


@router.get(
    "/sso/callback",
    status_code=200,
    response_model=SsoCallbackResponse,
    summary="SSO callback endpoint",
    responses={503: {"description": "Vault is locked"}},
)
async def sso_callback(
    request: Request,
    response: Response,
    code: str = Query(..., description="Authorization code from SSO provider"),
    state: str = Query(None, description="State parameter for CSRF protection"),
    redirect_uri: str = Query(None, description="Redirect URI used during authorization (for CLI auth)"),
    usecase: SsoLoginUseCase = Depends(get_sso_login_usecase),
):
    """
    SSO callback endpoint.

    This endpoint is called by the SSO provider after the user has authorized the application.
    It exchanges the authorization code for an access token and signs the user in.

    - **code**: The authorization code provided by the SSO provider
    - **state**: (Optional) State parameter for CSRF protection
    - **redirect_uri**: (Optional) Redirect URI used during authorization, required for CLI auth flows

    Returns user information and sets HTTP-only secure cookies with JWT tokens.
    """
    expected_state = request.cookies.get(SSO_STATE_COOKIE)
    rejection_reason = _state_rejection_reason(state, expected_state)
    if rejection_reason:
        # The body stays generic so a forged state learns nothing. The reason goes
        # to the log only, and never carries the state itself — it is a CSRF token.
        logger.warning("Rejecting SSO callback: %s", rejection_reason)
        _revoke_sso_state(request, response)
        raise HTTPException(status_code=400, detail="Invalid SSO state")
    # The state is single-use: revoke it now, so it stays revoked even when the
    # code exchange below fails and the route raises.
    _revoke_sso_state(request, response)

    try:
        command = SsoLoginCommand(code=code, redirect_uri=redirect_uri)
        result = await usecase.execute(command)

        # Set JWT tokens in HTTP-only cookies (not accessible by JavaScript)
        is_secure = get_cookie_secure_setting()

        response.set_cookie(
            key="access_token",
            value=result.jwt_token,
            httponly=True,
            secure=is_secure,  # HTTPS only in production
            samesite="strict",  # CSRF protection
            max_age=get_jwt_access_token_expiration_seconds(),
        )

        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=is_secure,  # HTTPS only in production
            samesite="strict",
            max_age=get_jwt_refresh_token_expiration_seconds(),
        )

        # Set a non-httpOnly cookie that frontend can read to check auth status
        response.set_cookie(
            key="logged_in",
            value="true",
            httponly=False,  # JavaScript can read this
            secure=is_secure,
            samesite="strict",
            max_age=get_jwt_access_token_expiration_seconds(),
        )

        return SsoCallbackResponse(
            message="SSO authentication successful",
            user=SsoUserInfo(
                user_id=result.user_id,
                email=result.email,
                display_name=result.display_name,
                is_new_user=result.is_new_user,
            ),
        )
    except InvalidSsoCodeException as e:
        raise HTTPException(status_code=400, detail="SSO authentication failed") from e
    except SsoEncryptionUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in SSO callback")
        raise HTTPException(status_code=500, detail="Internal server error") from e
