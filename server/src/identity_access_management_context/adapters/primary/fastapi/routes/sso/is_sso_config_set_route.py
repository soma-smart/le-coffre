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
    Check whether SSO (Single Sign-On) has been configured.

    Intentionally anonymous: the login page calls this before authentication to
    show or hide the SSO button. Returns only ``is_set``, never any provider
    detail.
    """
    try:
        command = IsSsoConfigSetCommand()
        result = usecase.execute(command)
        return IsSsoConfigSetResponse(is_set=result.is_set)
    except Exception as e:
        logger.exception("Unexpected error in check SSO config")
        raise HTTPException(status_code=500, detail="Internal server error") from e
