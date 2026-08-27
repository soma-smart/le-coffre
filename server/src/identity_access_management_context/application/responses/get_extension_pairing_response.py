from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtensionPairingDetailsResponse:
    """What the approval page shows the user before they decide.

    Everything here except `device_name` is vouched for by the server.
    `device_name` is self-reported by the extension, so the page must label it
    as untrusted rather than present it as fact.
    """

    user_code: str
    device_name: str
    created_at: datetime
    expires_at: datetime
    created_from_ip: str | None
    is_resolved: bool
