import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_groups_usecase,
)
from identity_access_management_context.application.commands import ListGroupsCommand
from identity_access_management_context.application.use_cases import ListGroupsUseCase
from identity_access_management_context.domain.exceptions import (
    IdentityAccessManagementDomainError,
)
from shared_kernel.adapters.primary.dependencies import get_current_principal
from shared_kernel.domain.entities import ApiPrincipal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/groups", tags=["Browser Extension"])


class ExtensionGroupItem(BaseModel):
    id: UUID
    name: str
    is_personal: bool
    is_owner: bool


class ListExtensionGroupsResponse(BaseModel):
    groups: list[ExtensionGroupItem]
    total: int


@router.get(
    "",
    status_code=200,
    response_model=ListExtensionGroupsResponse,
    summary="List the groups the caller belongs to",
)
def list_extension_groups(
    principal: ApiPrincipal = Depends(get_current_principal),
    usecase: ListGroupsUseCase = Depends(get_list_groups_usecase),
):
    """
    List only the groups the caller owns or is a member of.

    - **Authentication**: an extension bearer token, or an access_token cookie

    Deliberately not `GET /groups`. That route answers with every group on the
    instance, including other people's personal groups and each group's full
    owner and member lists, and leaves the filtering to the browser. That is
    fine for the web app, whose session is already as privileged as the user.
    It is not fine for an extension token sitting in browser storage: the same
    containment that strips the admin role from this credential would be
    pointless if it could still map the whole organisation.

    Returns each group's id, name, whether it is personal, and whether the
    caller owns it, which is what the popup needs to offer a group picker and
    to decide whether to show "Add a password".
    """
    try:
        result = usecase.execute(ListGroupsCommand(include_personal=True, only_for_user_id=principal.user.user_id))

        groups = [
            ExtensionGroupItem(
                id=group.id,
                name=group.name,
                is_personal=group.is_personal,
                is_owner=principal.user.user_id in group.owners,
            )
            for group in result.groups
        ]
        return ListExtensionGroupsResponse(groups=groups, total=len(groups))
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error listing extension groups")
        raise HTTPException(status_code=500, detail="Internal server error") from e
