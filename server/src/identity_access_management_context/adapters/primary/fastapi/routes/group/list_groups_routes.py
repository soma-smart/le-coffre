from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
import logging
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_groups_usecase,
)
from identity_access_management_context.application.use_cases import ListGroupsUseCase
from shared_kernel.authentication import ValidatedUser, get_current_user


router = APIRouter(prefix="/groups", tags=["Group Management"])


class GroupItem(BaseModel):
    id: UUID
    name: str
    is_personal: bool
    user_id: UUID | None
    owners: list[UUID]


class ListGroupsResponse(BaseModel):
    groups: list[GroupItem]
    total: int


@router.get(
    "",
    status_code=200,
    response_model=ListGroupsResponse,
    summary="List all groups",
)
def list_groups(
    include_personal: bool = Query(
        True,
        description="Include personal groups in results. Set to false to only show shared groups.",
    ),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListGroupsUseCase = Depends(get_list_groups_usecase),
):
    """
    List all groups with optional filtering.

    - **include_personal**: Whether to include personal groups in the results (default: true)
    - **Authorization**: Bearer token required (access_token cookie)

    Returns a list of all groups (or only shared groups if include_personal=false).
    Each group includes:
    - id: The group's unique identifier
    - name: The group's name
    - is_personal: Whether this is a personal group
    - user_id: The owner user ID (for personal groups) or null (for shared groups)
    - owners: List of user IDs who are owners of this group
    """
    try:
        groups_with_owners = usecase.execute(include_personal=include_personal)

        group_items = [
            GroupItem(
                id=group.id,
                name=group.name,
                is_personal=group.is_personal,
                user_id=group.user_id,
                owners=group.owners,
            )
            for group in groups_with_owners.groups
        ]

        return ListGroupsResponse(
            groups=group_items,
            total=len(group_items),
        )

    except Exception as e:
        logging.error(f"Error listing groups: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
