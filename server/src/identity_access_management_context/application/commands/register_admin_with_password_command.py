from dataclasses import dataclass
from uuid import UUID


@dataclass
class RegisterAdminWithPasswordCommand:
    id: UUID
    email: str
    password: str
    display_name: str
