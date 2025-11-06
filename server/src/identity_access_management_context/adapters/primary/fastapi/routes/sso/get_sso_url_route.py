from fastapi import APIRouter, Depends
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_sso_url_usecase,
)

from identity_access_management_context.application.use_cases import GetSsoAuthorizeUrlUseCase


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/sso/url", status_code=200, summary="Get SSO authorization URL")
async def get_sso_url(
    usecase: GetSsoAuthorizeUrlUseCase = Depends(get_sso_url_usecase),
):
    """
    Get the SSO authorization URL.

    Returns the SSO authorization URL.
    """
    return await usecase.execute()
