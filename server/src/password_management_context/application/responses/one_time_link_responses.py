from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreatedOneTimeLinkResponse:
    """Returned once, at creation: the only time the raw token ever leaves the server."""

    id: UUID
    token: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True)
class ConsumedOneTimeLinkResponse:
    """The payload handed to the anonymous reader."""

    name: str
    password: str = field(repr=False)
    login: str | None
    url: str | None


@dataclass(frozen=True)
class OneTimeLinkSummaryResponse:
    """Owner-facing view of a link. Deliberately carries no token, not even hashed."""

    id: UUID
    password_id: UUID
    created_by_user_id: UUID
    created_at: datetime
    expires_at: datetime
    read_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class ListOneTimeLinksResponse:
    """A bounded page of links plus how many exist in total.

    `total` is what lets the owner see that older links exist beyond the ones
    returned, rather than silently believing the list is complete. `active` and
    `max_active` let the UI show how much of the cap is used without having to
    re-derive it from a truncated list.
    """

    links: list[OneTimeLinkSummaryResponse]
    total: int
    active: int
    max_active: int
