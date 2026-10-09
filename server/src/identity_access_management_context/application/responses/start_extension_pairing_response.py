from dataclasses import dataclass
from datetime import datetime


@dataclass
class StartedExtensionPairingResponse:
    user_code: str
    expires_at: datetime
    poll_interval_seconds: int
