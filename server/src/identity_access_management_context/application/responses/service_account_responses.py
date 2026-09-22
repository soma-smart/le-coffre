from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreatedServiceAccountResponse:
    """Returned once, at creation."""

    id: UUID
    group_id: UUID
    name: str
    created_at: datetime
    token: str = field(repr=False)


@dataclass(frozen=True)
class RegeneratedServiceAccountTokenResponse:
    """Returned once, at regeneration. The account keeps its id, name and group."""

    id: UUID
    rotated_at: datetime
    token: str = field(repr=False)


@dataclass(frozen=True)
class ServiceAccountSummaryResponse:
    """Manager-facing view of an account. Deliberately carries no token, not even hashed.

    ``created_at`` and the creator fields are optional because they come from the
    account's creation event rather than from its row: an account whose event is
    missing still lists, with those fields empty.
    """

    id: UUID
    group_id: UUID
    name: str
    created_by_user_id: UUID | None
    created_by_display_name: str | None
    created_at: datetime | None
    revoked_at: datetime | None
    is_active: bool


@dataclass(frozen=True)
class ListServiceAccountsResponse:
    """A group's accounts, plus how much of the cap is used.

    ``active`` and ``max_active`` let a caller show "2 of 3 used" without
    re-deriving it from a list that may be filtered to active accounts only.
    """

    service_accounts: list[ServiceAccountSummaryResponse]
    total: int
    active: int
    max_active: int
