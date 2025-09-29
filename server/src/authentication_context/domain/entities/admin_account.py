from uuid import UUID
from dataclasses import dataclass


@dataclass
class AdminAccount:
    id: UUID
    email: str
    password_hash: str
    display_name: str
