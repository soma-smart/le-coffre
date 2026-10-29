from dataclasses import dataclass
from datetime import datetime

from vault_management_context.domain.value_objects import ShareLinkStatus


@dataclass(frozen=True)
class ShareLinkOverview:
    """What an administrator may know of one link: never a hash, share or token."""

    share_index: int
    status: ShareLinkStatus
    expires_at: datetime | None
    first_opened_at: datetime | None
    reopenable_until: datetime | None
    acknowledged_at: datetime | None
    open_count: int


@dataclass(frozen=True)
class ShareLinksOverview:
    setup_id: str
    nb_shares: int
    threshold: int
    created_at: datetime | None
    links: list[ShareLinkOverview]
    counts: dict[ShareLinkStatus, int]
