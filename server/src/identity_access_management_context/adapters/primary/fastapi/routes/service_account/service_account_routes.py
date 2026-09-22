import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette import status

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_service_account_usecase,
    get_list_service_accounts_usecase,
    get_revoke_service_account_usecase,
    get_rotate_service_account_token_usecase,
)
from identity_access_management_context.application.commands import (
    CreateServiceAccountCommand,
    ListServiceAccountsCommand,
    RevokeServiceAccountCommand,
    RotateServiceAccountTokenCommand,
)
from identity_access_management_context.application.gateways import ServiceAccountRepositoryException
from identity_access_management_context.application.use_cases import (
    CreateServiceAccountUseCase,
    ListServiceAccountsUseCase,
    RevokeServiceAccountUseCase,
    RotateServiceAccountTokenUseCase,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    IdentityAccessManagementDomainError,
    InvalidServiceAccountNameError,
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
    TooManyActiveServiceAccountsError,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
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


class RotatedServiceAccountToken(BaseModel):
    id: UUID
    token: str


class ServiceAccountSummary(BaseModel):
    id: UUID
    group_id: UUID
    name: str
    created_by_user_id: UUID | None
    created_by_user_name: str | None
    created_at: datetime | None
    revoked_at: datetime | None


class ListServiceAccounts(BaseModel):
    items: list[ServiceAccountSummary]


def _raise_for(error: Exception) -> None:
    """Map a domain or repository failure onto its HTTP status."""
    if isinstance(error, GroupNotFoundException | ServiceAccountNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, UserNotOwnerOfGroupException):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(
        error,
        TooManyActiveServiceAccountsError | ServiceAccountAlreadyRevokedException | ServiceAccountRepositoryException,
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, InvalidServiceAccountNameError | IdentityAccessManagementDomainError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    raise error


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
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

    Only a group owner or an administrator may do this. The token is returned
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
    except Exception as e:
        _raise_for(e)
        logger.exception("Unexpected error in create service account")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.get(
    "",
    response_model=ListServiceAccounts,
    summary="List a group's service accounts",
)
def list_service_accounts(
    group_id: UUID = Query(description="Group whose service accounts to list"),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListServiceAccountsUseCase = Depends(get_list_service_accounts_usecase),
) -> ListServiceAccounts:
    """
    List a group's service accounts, revoked ones included.

    - **group_id**: Group whose service accounts to list

    Only a group owner or an administrator may do this. No token is returned,
    hashed or otherwise.
    """
    try:
        command = ListServiceAccountsCommand(
            requesting_user=current_user.to_authenticated_user(),
            group_id=group_id,
        )
        response = usecase.execute(command)
        return ListServiceAccounts(
            items=[
                ServiceAccountSummary(
                    id=item.id,
                    group_id=item.group_id,
                    name=item.name,
                    created_by_user_id=item.created_by_user_id,
                    created_by_user_name=item.created_by_user_name,
                    created_at=item.created_at,
                    revoked_at=item.revoked_at,
                )
                for item in response.items
            ]
        )
    except Exception as e:
        _raise_for(e)
        logger.exception("Unexpected error in list service accounts")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.post(
    "/{service_account_id}/rotate",
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

    Only a group owner or an administrator may do this. The account keeps its
    id, name, group and history. The new token is returned here and never again.
    """
    try:
        command = RotateServiceAccountTokenCommand(
            requesting_user=current_user.to_authenticated_user(),
            service_account_id=service_account_id,
        )
        response = usecase.execute(command)
        return RotatedServiceAccountToken(id=response.id, token=response.token)
    except Exception as e:
        _raise_for(e)
        logger.exception("Unexpected error in rotate service account token")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.delete(
    "/{service_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a service account",
)
def revoke_service_account(
    service_account_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RevokeServiceAccountUseCase = Depends(get_revoke_service_account_usecase),
) -> None:
    """
    Revoke a service account.

    Only a group owner or an administrator may do this. The account stops being
    active but its row survives, so the revocation stays auditable.
    """
    try:
        command = RevokeServiceAccountCommand(
            requesting_user=current_user.to_authenticated_user(),
            service_account_id=service_account_id,
        )
        usecase.execute(command)
    except Exception as e:
        _raise_for(e)
        logger.exception("Unexpected error in revoke service account")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
