from dataclasses import dataclass
from datetime import datetime
from typing import NoReturn
from uuid import UUID

from .base_password_event import BasePasswordEvent


@dataclass
class OneTimeLinkExpiredEvent(BasePasswordEvent):
    """Domain event: a one-time link ran out unread, and its creator asked to be told.

    Published only, never stored in the audit log: nobody acted, the clock did.
    Raised by the periodic expiry sweep, at most once per link.
    """

    link_id: UUID
    created_by_user_id: UUID
    password_name: str
    expires_at: datetime

    def get_actor_user_id(self) -> UUID:
        return self.created_by_user_id

    def to_event_data(self) -> NoReturn:
        raise NotImplementedError("OneTimeLinkExpiredEvent is published only, it is not an audit event")
