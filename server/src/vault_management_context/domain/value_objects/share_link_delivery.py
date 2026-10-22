from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ShareLinkDelivery:
    """The outcome of handing a sealed share out.

    `reopened` tells the custodian that this link had been opened before, at
    `first_delivered_at`: by them, or by someone else holding the link.
    """

    first_delivered_at: datetime
    reopenable_until: datetime
    reopened: bool
