from fastapi import APIRouter, Depends, HTTPException, Query
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_sso_login_usecase,
)
from identity_access_management_context.application.commands.sso_login_command import SsoLoginCommand
from identity_access_management_context.application.use_cases import SsoLoginUseCase
from identity_access_management_context.domain.exceptions import InvalidSsoCodeException


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/sso/callback", status_code=200, summary="SSO callback endpoint")
async def sso_callback(
    code: str = Query(..., description="Authorization code from SSO provider"),
    state: str = Query(None, description="State parameter for CSRF protection"),
    usecase: SsoLoginUseCase = Depends(get_sso_login_usecase),
):
    """
    SSO callback endpoint.

    This endpoint is called by the SSO provider after the user has authorized the application.
    It exchanges the authorization code for an access token and signs the user in.

    - **code**: The authorization code provided by the SSO provider
    - **state**: (Optional) State parameter for CSRF protection

    Returns a JWT for the authenticated user.
    """
    try:
        command = SsoLoginCommand(code=code)
        result = await usecase.execute(command)
        return {
            "access_token": result.jwt_token,
            "token_type": "bearer",
            "user": {
                "user_id": str(result.user_id),
                "email": result.email,
                "display_name": result.display_name,
                "is_new_user": result.is_new_user,
            }
        }
    except InvalidSsoCodeException as e:
        raise HTTPException(status_code=400, detail=f"SSO authentication failed: {str(e)}")
