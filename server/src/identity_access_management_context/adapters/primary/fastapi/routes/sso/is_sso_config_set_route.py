import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_is_sso_config_set_usecase,
)
from identity_access_management_context.application.commands import IsSsoConfigSetCommand
from identity_access_management_context.application.use_cases import (
    IsSsoConfigSetUseCase,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class IsSsoConfigSetResponse(BaseModel):
    """Response indicating if SSO is configured."""

    is_set: bool


@router.get(
    "/sso/is-configured",
    response_model=IsSsoConfigSetResponse,
    status_code=200,
    summary="Check if SSO is configured",
)
def is_sso_config_set(
    usecase: IsSsoConfigSetUseCase = Depends(get_is_sso_config_set_usecase),
):
    """
    Check if SSO (Single Sign-On) configuration is set.

    Returns a boolean indicating whether the system has been configured with SSO settings.

    - **Authorization**: Bearer token with admin role required
    - **Returns**: `is_set` - True if SSO is configured, False otherwise

    **Note**: Only administrators can check SSO configuration status.
    """
    try:
        command = IsSsoConfigSetCommand()
        result = usecase.execute(command)
        return IsSsoConfigSetResponse(is_set=result.is_set)
    except Exception as e:
        logger.exception("Unexpected error in check SSO config")
        raise HTTPException(status_code=500, detail="Internal server error") from e
