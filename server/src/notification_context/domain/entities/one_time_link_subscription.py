from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class OneTimeLinkSubscription:
    """A link creator's request to be emailed about what becomes of one one-time link.

    It only lives while the link can still be read: it is removed as soon as the link
    was read or has expired, whichever this context learns first, so that one link
    never produces two emails.
    """

    link_id: UUID
    user_id: UUID
    # Copied from the link when subscribing (it never changes): lets the expiry sweep
    # find the subscriptions to look at without asking the password context first.
    expires_at: datetime
    notify_on_read: bool = False
    notify_on_expiry: bool = False

    def is_empty(self) -> bool:
        return not (self.notify_on_read or self.notify_on_expiry)
