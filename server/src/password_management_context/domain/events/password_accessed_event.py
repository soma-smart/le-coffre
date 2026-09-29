from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from shared_kernel.domain.value_objects import CredentialKind

from .base_password_event import BasePasswordEvent


class PasswordAccessedEventData(TypedDict):
    """Typed structure for PasswordAccessedEvent storage data"""

    password_id: str
    password_name: str
    credential_kind: str


@dataclass
class PasswordAccessedEvent(BasePasswordEvent):
    """Domain event for password access.

    `credential_kind` says whether the read came through the user's own
    session or through a browser-extension token. The two carry different
    authority and different theft models, and a trail that cannot tell them
    apart cannot answer "what did the stolen extension token read".
    """

    password_name: str
    accessed_by_user_id: UUID
    credential_kind: CredentialKind

    def get_actor_user_id(self) -> UUID:
        return self.accessed_by_user_id

    def to_event_data(self) -> PasswordAccessedEventData:
        return {
            "password_id": str(self.password_id),
            "password_name": self.password_name,
            "credential_kind": self.credential_kind.value,
        }
