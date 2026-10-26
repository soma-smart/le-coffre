from enum import Enum


class ShareLinkStatus(Enum):
    """Where a share link stands for the administrator following the setup.

    Derived, never stored: the link row is deleted on acknowledgement and purged
    once expired, so the audit trail has to complete what the table still says.
    """

    PENDING = "PENDING"
    OPENED = "OPENED"
    OPENED_UNCONFIRMED = "OPENED_UNCONFIRMED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EXPIRED = "EXPIRED"
