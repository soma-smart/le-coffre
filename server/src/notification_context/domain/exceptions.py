class NotificationDomainError(Exception):
    """Base class for the notification context's domain errors"""


class OneTimeLinkNotFoundError(NotificationDomainError):
    """The link does not exist, or it was not issued by the user asking to follow it.

    Both cases are reported the same way, so nobody learns about other users' links.
    """

    def __init__(self) -> None:
        super().__init__("The one-time link does not exist")


class OneTimeLinkNoLongerActiveError(NotificationDomainError):
    """The link was already read, revoked or expired: there is nothing left to follow."""

    def __init__(self) -> None:
        super().__init__("The one-time link was already read, revoked or expired")
