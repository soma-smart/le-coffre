import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_consume_one_time_link_usecase,
    get_create_one_time_link_usecase,
    get_list_one_time_links_usecase,
    get_revoke_one_time_link_usecase,
)
from password_management_context.application.commands import (
    ConsumeOneTimeLinkCommand,
    CreateOneTimeLinkCommand,
    ListOneTimeLinksCommand,
    RevokeOneTimeLinkCommand,
)
from password_management_context.application.use_cases import (
    ConsumeOneTimeLinkUseCase,
    CreateOneTimeLinkUseCase,
    ListOneTimeLinksUseCase,
    RevokeOneTimeLinkUseCase,
)
from password_management_context.domain.exceptions import (
    InvalidOneTimeLinkTokenError,
    NotPasswordOwnerError,
    OneTimeLinkAlreadyUsedError,
    OneTimeLinkExpiredError,
    OneTimeLinkNotFoundError,
    OneTimeLinkRevokedError,
    PasswordEncryptionUnavailableError,
    PasswordManagementDomainError,
    PasswordNotFoundError,
    TooManyActiveOneTimeLinksError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

owner_router = APIRouter(prefix="/passwords", tags=["Password Management"])
public_router = APIRouter(prefix="/one-time-links", tags=["Password Management"])

# Every "this link cannot be redeemed" case answers with this exact body.
# Telling apart unknown, expired, used and revoked would let an anonymous
# caller probe which tokens exist.
_UNUSABLE_LINK_DETAIL = "This link is invalid or has already been used"


class CreateOneTimeLinkRequest(BaseModel):
    lifetime_seconds: int | None = Field(
        default=None,
        description="How long the link stays valid. Defaults to 24h; bounded by the domain to 5 minutes .. 7 days.",
    )


class CreateOneTimeLinkResponse(BaseModel):
    id: UUID
    token: str
    expires_at: datetime


class OneTimeLinkSummary(BaseModel):
    id: UUID
    password_id: UUID
    created_by_user_id: UUID
    created_at: datetime
    expires_at: datetime
    read_at: datetime | None
    revoked_at: datetime | None


class ListOneTimeLinksResponseModel(BaseModel):
    links: list[OneTimeLinkSummary]
    total: int = Field(description="How many links exist in total, which may exceed the number returned.")
    active: int = Field(description="How many links are still redeemable right now.")
    max_active: int = Field(description="How many links may be active at once for one password.")


class ConsumeOneTimeLinkRequest(BaseModel):
    token: str


class ConsumeOneTimeLinkResponse(BaseModel):
    name: str
    password: str
    login: str | None
    url: str | None


@owner_router.post(
    "/{password_id}/one-time-links",
    response_model=CreateOneTimeLinkResponse,
    status_code=201,
    summary="Generate a one-time link for a password",
)
def create_one_time_link(
    password_id: UUID,
    request: CreateOneTimeLinkRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: CreateOneTimeLinkUseCase = Depends(get_create_one_time_link_usecase),
):
    """
    Generate a single-use link granting anonymous read access to one password.

    - **password_id**: UUID of the password to share
    - **lifetime_seconds**: optional validity window, 24h by default
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    The token is returned here and never again: only its hash is stored.

    Answers 409 when the password already has the maximum number of links that
    are still redeemable. Read, revoked and expired links do not count.
    """
    try:
        command = CreateOneTimeLinkCommand(
            password_id=password_id,
            requesting_user_id=current_user.user_id,
            lifetime_seconds=request.lifetime_seconds,
        )
        result = usecase.execute(command)
        return CreateOneTimeLinkResponse(id=result.id, token=result.token, expires_at=result.expires_at)
    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail="Password does not exist") from e
    except NotPasswordOwnerError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except TooManyActiveOneTimeLinksError as e:
        # 409 rather than 400: the request is well formed, it conflicts with the
        # password's current state, and the owner can resolve it by revoking one.
        raise HTTPException(status_code=409, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in create one-time link")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@owner_router.get(
    "/{password_id}/one-time-links",
    response_model=ListOneTimeLinksResponseModel,
    status_code=200,
    summary="List the one-time links issued for a password",
)
def list_one_time_links(
    password_id: UUID,
    include_inactive: bool = False,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListOneTimeLinksUseCase = Depends(get_list_one_time_links_usecase),
):
    """
    List the one-time links issued for a password.

    - **password_id**: UUID of the password
    - **include_inactive**: also return spent, revoked and expired links
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    Returns only the still-redeemable links by default: those are the ones the
    owner can revoke, and their number is bounded by the active-link cap. Passing
    `include_inactive` returns the recent history too, capped, since spent links
    are kept indefinitely. `active`, `max_active` and `total` describe the whole
    set regardless of the filter. Tokens are never returned, not even hashed.
    """
    try:
        command = ListOneTimeLinksCommand(
            password_id=password_id,
            requesting_user_id=current_user.user_id,
            include_inactive=include_inactive,
        )
        result = usecase.execute(command)
        return ListOneTimeLinksResponseModel(
            links=[
                OneTimeLinkSummary(
                    id=link.id,
                    password_id=link.password_id,
                    created_by_user_id=link.created_by_user_id,
                    created_at=link.created_at,
                    expires_at=link.expires_at,
                    read_at=link.read_at,
                    revoked_at=link.revoked_at,
                )
                for link in result.links
            ],
            total=result.total,
            active=result.active,
            max_active=result.max_active,
        )
    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail="Password does not exist") from e
    except NotPasswordOwnerError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in list one-time links")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@public_router.delete(
    "/{link_id}",
    status_code=204,
    summary="Revoke a one-time link",
)
def revoke_one_time_link(
    link_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RevokeOneTimeLinkUseCase = Depends(get_revoke_one_time_link_usecase),
):
    """
    Revoke a one-time link that has not been read yet.

    - **link_id**: UUID of the link to revoke
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    Links that were already read cannot be revoked: their read timestamp is audit data.
    """
    try:
        command = RevokeOneTimeLinkCommand(link_id=link_id, requesting_user_id=current_user.user_id)
        usecase.execute(command)
    except OneTimeLinkNotFoundError as e:
        raise HTTPException(status_code=404, detail="Link does not exist") from e
    except NotPasswordOwnerError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in revoke one-time link")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@public_router.post(
    "/consume",
    response_model=ConsumeOneTimeLinkResponse,
    status_code=200,
    summary="Redeem a one-time link",
    responses={503: {"description": "Vault is locked"}},
)
def consume_one_time_link(
    request: ConsumeOneTimeLinkRequest,
    usecase: ConsumeOneTimeLinkUseCase = Depends(get_consume_one_time_link_usecase),
):
    """
    Redeem a one-time link and return the secret it points at.

    - **token**: the secret carried by the link
    - **Authentication**: intentionally anonymous. The token in the body is the
      only credential; recipients are outside the vault by design.

    The token is sent in the body rather than the URL so it stays out of server
    logs and Referer headers, and this is a POST so that link scanners and mail
    previewers cannot burn the link by merely following the URL.

    A locked vault answers 503 without consuming the link, so the recipient can
    retry once it is unlocked.
    """
    try:
        result = usecase.execute(ConsumeOneTimeLinkCommand(token=request.token))
        return ConsumeOneTimeLinkResponse(
            name=result.name,
            password=result.password,
            login=result.login,
            url=result.url,
        )
    except (
        OneTimeLinkNotFoundError,
        OneTimeLinkExpiredError,
        OneTimeLinkAlreadyUsedError,
        OneTimeLinkRevokedError,
        InvalidOneTimeLinkTokenError,
    ) as e:
        raise HTTPException(status_code=404, detail=_UNUSABLE_LINK_DETAIL) from e
    except PasswordEncryptionUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in consume one-time link")
        raise HTTPException(status_code=500, detail="Internal server error") from e
