from datetime import datetime, timezone
from typing import Dict, List, Optional

from vault_management_context.application.gateways import ShareRepository
from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import UnlockSessionId


class FakeShareRepository(ShareRepository):
    def __init__(self):
        self._shares: Dict[UnlockSessionId, List[Share]] = {}
        self._last_share_timestamps: Dict[UnlockSessionId, datetime] = {}

    def get_all(self, session_id: UnlockSessionId) -> List[Share]:
        return self._shares.get(session_id, []).copy()

    def add(self, session_id: UnlockSessionId, shares: List[Share]) -> None:
        self._shares.setdefault(session_id, []).extend(shares)
        self._last_share_timestamps[session_id] = datetime.now(timezone.utc)

    def clear(self) -> None:
        self._shares = {}
        self._last_share_timestamps = {}

    def get_last_share_timestamp(self, session_id: UnlockSessionId) -> Optional[datetime]:
        return self._last_share_timestamps.get(session_id)
