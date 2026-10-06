import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from starlette import status

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_service_accounts_usecase,
)
from identity_access_management_context.application.commands import ListServiceAccountsCommand
from identity_access_management_context.application.use_cases import ListServiceAccountsUseCase
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iam/service-accounts", tags=["Service Accounts"])


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
    active: int = Field(description="How many of the listed accounts are still usable.")
    max_active: int = Field(description="How many accounts may be active at once in one group.")


@router.get(
    "",
    response_model=ListServiceAccounts,
    summary="List a group's service accounts",
)
def list_service_accounts(
    group_id: UUID | None = Query(default=None, description="Group to filter on; every reachable group when absent"),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListServiceAccountsUseCase = Depends(get_list_service_accounts_usecase),
) -> ListServiceAccounts:
    """
    List service accounts, revoked ones included.

    - **group_id**: Group to filter on. Omit it to list every group the caller
      can manage: those they own, or all of them for an administrator.

    `active` counts the usable accounts among those listed, and is only comparable
    with `max_active` when `group_id` is set: an unscoped listing spans several
    groups, each with its own budget.

    Filtering to one group requires being its owner. Leaving it unscoped also
    admits an administrator, who then sees every group's accounts — listing
    carries no token, so this is a metadata view, never a way to a credential.
    No token is returned, hashed or otherwise.
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
            ],
            active=response.active,
            max_active=response.max_active,
        )
    except GroupNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in list service accounts")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
