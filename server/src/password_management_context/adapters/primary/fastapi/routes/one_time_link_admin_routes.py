import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_my_one_time_links_usecase,
    get_list_one_time_links_for_admin_usecase,
    get_revoke_all_one_time_links_for_user_usecase,
    get_revoke_one_time_link_for_admin_usecase,
)
from password_management_context.application.commands import (
    ListMyOneTimeLinksCommand,
    ListOneTimeLinksForAdminCommand,
    RevokeAllOneTimeLinksForUserCommand,
    RevokeOneTimeLinkForAdminCommand,
)
from password_management_context.application.responses import ListOneTimeLinkAuditResponse
from password_management_context.application.use_cases import (
    ListMyOneTimeLinksUseCase,
    ListOneTimeLinksForAdminUseCase,
    RevokeAllOneTimeLinksForUserUseCase,
    RevokeOneTimeLinkForAdminUseCase,
)
from password_management_context.domain.exceptions import (
    OneTimeLinkNotFoundError,
    PasswordManagementDomainError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["Password Management"])
mine_router = APIRouter(prefix="/one-time-links", tags=["Password Management"])


class OneTimeLinkAuditItem(BaseModel):
    id: UUID
    password_id: UUID
    password_name: str | None = Field(description="None when the password has since been deleted.")
    created_by_user_id: UUID
    created_by_email: str | None
    created_at: datetime
    expires_at: datetime
    read_at: datetime | None
    revoked_at: datetime | None


class ListOneTimeLinkAuditResponseModel(BaseModel):
    links: list[OneTimeLinkAuditItem]
    total: int = Field(description="How many links match, which may exceed the number returned.")


class RevokeAllOneTimeLinksResponse(BaseModel):
    revoked_count: int


def _to_model(result: ListOneTimeLinkAuditResponse) -> ListOneTimeLinkAuditResponseModel:
    return ListOneTimeLinkAuditResponseModel(
        links=[
            OneTimeLinkAuditItem(
                id=link.id,
                password_id=link.password_id,
                password_name=link.password_name,
                created_by_user_id=link.created_by_user_id,
                created_by_email=link.created_by_email,
                created_at=link.created_at,
                expires_at=link.expires_at,
                read_at=link.read_at,
                revoked_at=link.revoked_at,
            )
            for link in result.links
        ],
        total=result.total,
    )


@mine_router.get(
    "/mine",
    response_model=ListOneTimeLinkAuditResponseModel,
    status_code=200,
    summary="List the one-time links the caller issued",
)
def list_my_one_time_links(
    include_inactive: bool = Query(False, description="Also return spent, revoked and expired links"),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListMyOneTimeLinksUseCase = Depends(get_list_my_one_time_links_usecase),
):
    """
    List every one-time link the calling user issued, across all passwords.

    - **include_inactive**: also return spent, revoked and expired links
    - **Authentication**: Requires authentication via access_token cookie

    Returns only the still-redeemable links by default. Tokens are never returned.
    """
    try:
        command = ListMyOneTimeLinksCommand(
            requesting_user_id=current_user.user_id,
            include_inactive=include_inactive,
        )
        return _to_model(usecase.execute(command))
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in list my one-time links")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@admin_router.get(
    "/one-time-links",
    response_model=ListOneTimeLinkAuditResponseModel,
    status_code=200,
    summary="List every one-time link in the vault (admin only)",
)
def list_one_time_links_for_admin(
    include_inactive: bool = Query(False, description="Also return spent, revoked and expired links"),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListOneTimeLinksForAdminUseCase = Depends(get_list_one_time_links_for_admin_usecase),
):
    """
    List the one-time links issued anywhere in the vault.

    - **include_inactive**: also return spent, revoked and expired links
    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can access this endpoint

    Every active link is an outstanding anonymous read grant, so this is the view
    that says how much of that access is currently open. Tokens are never returned.
    """
    try:
        command = ListOneTimeLinksForAdminCommand(
            requesting_user=current_user.to_authenticated_user(),
            include_inactive=include_inactive,
        )
        return _to_model(usecase.execute(command))
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in list one-time links for admin")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@admin_router.delete(
    "/one-time-links/{link_id}",
    status_code=204,
    summary="Revoke any one-time link (admin only)",
)
def revoke_one_time_link_for_admin(
    link_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RevokeOneTimeLinkForAdminUseCase = Depends(get_revoke_one_time_link_for_admin_usecase),
):
    """
    Revoke a one-time link regardless of who issued it.

    - **link_id**: UUID of the link to revoke
    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can access this endpoint

    Links that were already read cannot be revoked: their read timestamp is audit data.
    """
    try:
        command = RevokeOneTimeLinkForAdminCommand(
            link_id=link_id,
            requesting_user=current_user.to_authenticated_user(),
        )
        usecase.execute(command)
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except OneTimeLinkNotFoundError as e:
        raise HTTPException(status_code=404, detail="Link does not exist") from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in revoke one-time link for admin")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@admin_router.delete(
    "/users/{user_id}/one-time-links",
    response_model=RevokeAllOneTimeLinksResponse,
    status_code=200,
    summary="Revoke every live one-time link a user issued (admin only)",
)
def revoke_all_one_time_links_for_user(
    user_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RevokeAllOneTimeLinksForUserUseCase = Depends(get_revoke_all_one_time_links_for_user_usecase),
):
    """
    Revoke every still-redeemable link issued by one user, in a single call.

    - **user_id**: UUID of the user whose links are being cut
    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can access this endpoint

    Meant for the moment someone loses their access: the links they handed out
    would otherwise outlive their account. Already-read links are left untouched.
    """
    try:
        command = RevokeAllOneTimeLinksForUserCommand(
            target_user_id=user_id,
            requesting_user=current_user.to_authenticated_user(),
        )
        return RevokeAllOneTimeLinksResponse(revoked_count=usecase.execute(command))
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in revoke all one-time links for user")
        raise HTTPException(status_code=500, detail="Internal server error") from e
