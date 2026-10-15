from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RetrievedShareLink:
    setup_id: str
    share_index: int
    sealed_share: str
    first_retrieved_at: datetime
    reopenable_until: datetime
    reopened: bool
