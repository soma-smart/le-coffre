from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from authentication_context.adapters.primary.fastapi.app_dependencies import (
    set_sso_settings_usecase,
)

from authentication_context.application.use_cases import SsoSetSettingsUseCase
from authentication_context.domain.exceptions import InvalidSsoSettingsException


router = APIRouter(prefix="/auth", tags=["Authentication"])


class SetSsoSettingsRequest(BaseModel):
    client_id: str
    client_secret: str


@router.post("/sso/settings", status_code=200, summary="Set SSO settings")
def set_sso_settings(
    request: SetSsoSettingsRequest,
    usecase: SsoSetSettingsUseCase = Depends(set_sso_settings_usecase),
):
    """
    Set the SSO settings.

    - **client_id**: The SSO client ID
    - **client_secret**: The SSO client secret
    """
    try:
        return usecase.execute(
            client_id=request.client_id,
            client_secret=request.client_secret,
        )
    except InvalidSsoSettingsException as e:
        raise HTTPException(status_code=400, detail=str(e))
