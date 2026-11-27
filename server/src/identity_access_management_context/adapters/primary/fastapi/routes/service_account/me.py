import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette import status

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_service_account_me_usecase,
)
from identity_access_management_context.application.commands import GetServiceAccountMeCommand
from identity_access_management_context.application.use_cases import GetServiceAccountMeUseCase
from shared_kernel.adapters.primary.dependencies import get_current_service_account
from shared_kernel.domain.entities import AuthenticatedPrincipal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iam/service-accounts", tags=["Service Accounts"])


class ServiceAccountMe(BaseModel):
    service_account_id: UUID
    name: str
    group_id: UUID
    group_name: str


@router.get(
    "/me",
    response_model=ServiceAccountMe,
    summary="Tell which service account a token belongs to",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "The Bearer token is missing, invalid, revoked or regenerated",
        }
    },
)
def get_service_account_me(
    service_account: AuthenticatedPrincipal = Depends(get_current_service_account),
    usecase: GetServiceAccountMeUseCase = Depends(get_service_account_me_usecase),
) -> ServiceAccountMe:
    """
    Check that a token works, and see which account and which group it opens.

    - **Authentication**: `Authorization: Bearer <token>` only. A session cookie is
      not accepted here: this route answers for machines.

    Answers 200 as soon as the token is valid, whether or not the vault is unlocked.
    """
    try:
        response = usecase.execute(GetServiceAccountMeCommand(service_account_id=service_account.principal_id))
        return ServiceAccountMe(
            service_account_id=response.service_account_id,
            name=response.name,
            group_id=response.group_id,
            group_name=response.group_name,
        )
    except Exception as e:
        logger.exception("Unexpected error in get service account me")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
