from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class PasswordAccessedEventData(TypedDict):
    """Typed structure for PasswordAccessedEvent storage data"""

    password_id: str
    password_name: str
    credential_id: str | None


@dataclass
class PasswordAccessedEvent(BasePasswordEvent):
    """Domain event for password access.

    `credential_id` names the stored credential the read came through, None
    for the caller's own session. A trail that cannot tell them apart cannot
    answer "what did the stolen token read".

    Events recorded before it carry `credential_kind` instead, "session" or
    "extension".
    """

    password_name: str
    accessed_by_principal_id: UUID
    credential_id: UUID | None

    def get_actor_principal_id(self) -> UUID:
        return self.accessed_by_principal_id

    def to_event_data(self) -> PasswordAccessedEventData:
        return {
            "password_id": str(self.password_id),
            "password_name": self.password_name,
            "credential_id": None if self.credential_id is None else str(self.credential_id),
        }
