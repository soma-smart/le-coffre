from dataclasses import dataclass
from uuid import UUID


@dataclass
class RegisterWithPasswordCommand:
    id: UUID
    email: str
    password: str
    display_name: str
