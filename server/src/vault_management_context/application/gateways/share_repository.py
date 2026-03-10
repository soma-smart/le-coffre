from datetime import datetime
from typing import Protocol

from vault_management_context.domain.entities import Share


class ShareRepository(Protocol):
    def get_all(self) -> list[Share]: ...

    def add(self, shares: list[Share]) -> None: ...

    def clear(self) -> None: ...

    def get_last_share_timestamp(self) -> datetime | None: ...
