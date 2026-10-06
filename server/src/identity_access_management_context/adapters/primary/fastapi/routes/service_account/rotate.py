import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette import status

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_rotate_service_account_token_usecase,
)
from identity_access_management_context.application.commands import RotateServiceAccountTokenCommand
from identity_access_management_context.application.use_cases import RotateServiceAccountTokenUseCase
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import csrf_scheme, get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iam/service-accounts", tags=["Service Accounts"])


class RotatedServiceAccountToken(BaseModel):
    id: UUID
    token: str


@router.post(
    "/{service_account_id}/rotate",
    dependencies=[Depends(csrf_scheme)],
    response_model=RotatedServiceAccountToken,
    summary="Rotate a service account's token",
)
def rotate_service_account_token(
    service_account_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RotateServiceAccountTokenUseCase = Depends(get_rotate_service_account_token_usecase),
) -> RotatedServiceAccountToken:
    """
    Replace a service account's token, retiring the previous one.

    Only a group owner may do this — not even an administrator, since the new
    token this returns can read the group's passwords. The account keeps its
    id, name, group and history. The new token is returned here and never again.
    """
    try:
        command = RotateServiceAccountTokenCommand(
            requesting_user=current_user.to_authenticated_user(),
            service_account_id=service_account_id,
        )
        response = usecase.execute(command)
        return RotatedServiceAccountToken(id=response.id, token=response.token)
    except (GroupNotFoundException, ServiceAccountNotFoundException) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ServiceAccountAlreadyRevokedException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in rotate service account token")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
