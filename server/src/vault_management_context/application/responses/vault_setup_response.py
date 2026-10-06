from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class IssuedShareLink:
    """A share link as handed to whoever ran the setup, the only time its token exists."""

    share_index: int
    token: str = field(repr=False)
    expires_at: datetime


@dataclass
class VaultSetupResponse:
    setup_id: str
    share_links: list[IssuedShareLink]
