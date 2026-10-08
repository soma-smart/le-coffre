import re
from dataclasses import dataclass

from vault_management_context.domain.exceptions import InvalidUnlockSessionIdError

# Generated client-side by the unlock page and shared by URL between the share
# holders. The minimum length keeps it hard to guess: anyone who knows the id can
# add shares to that session, and a single bad share makes it unusable.
UNLOCK_SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{16,64}$"
_UNLOCK_SESSION_ID_REGEX = re.compile(UNLOCK_SESSION_ID_PATTERN)


@dataclass(frozen=True)
class UnlockSessionId:
    """Identifies one unlock ceremony: the pending shares are pooled per session."""

    value: str

    def __post_init__(self) -> None:
        if not _UNLOCK_SESSION_ID_REGEX.fullmatch(self.value):
            raise InvalidUnlockSessionIdError()
