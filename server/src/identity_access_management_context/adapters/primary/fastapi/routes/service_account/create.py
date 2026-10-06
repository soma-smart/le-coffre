import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette import status

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_service_account_usecase,
)
from identity_access_management_context.application.commands import CreateServiceAccountCommand
from identity_access_management_context.application.use_cases import CreateServiceAccountUseCase
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    IdentityAccessManagementDomainError,
    TooManyActiveServiceAccountsError,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import csrf_scheme, get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iam/service-accounts", tags=["Service Accounts"])


class CreateServiceAccountRequest(BaseModel):
    group_id: UUID
    name: str


class CreatedServiceAccount(BaseModel):
    id: UUID
    group_id: UUID
    name: str
    token: str


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(csrf_scheme)],
    response_model=CreatedServiceAccount,
    summary="Create a service account on a group",
)
def create_service_account(
    request: CreateServiceAccountRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: CreateServiceAccountUseCase = Depends(get_create_service_account_usecase),
) -> CreatedServiceAccount:
    """
    Create a service account owned by a group.

    - **group_id**: Group that will own the service account
    - **name**: Name to give the service account

    Only a group owner may do this, not even an administrator, since the
    token this returns can read the group's passwords. The token is returned
    here and never again: only its hash is stored.
    """
    try:
        command = CreateServiceAccountCommand(
            requesting_user=current_user.to_authenticated_user(),
            group_id=request.group_id,
            name=request.name,
        )
        response = usecase.execute(command)
        return CreatedServiceAccount(
            id=response.id,
            group_id=response.group_id,
            name=response.name,
            token=response.token,
        )
    except GroupNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except TooManyActiveServiceAccountsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in create service account")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
