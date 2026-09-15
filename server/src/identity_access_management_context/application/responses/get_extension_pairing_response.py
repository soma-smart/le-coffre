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
    #: When this *request* stops being approvable, minutes away. Not the
    #: lifetime of the credential it would create.
    expires_at: datetime
    #: How long the credential itself would last. The approval page states this
    #: one: it is what the user is actually consenting to.
    access_lifetime_seconds: int
    created_from_ip: str | None
    is_resolved: bool
