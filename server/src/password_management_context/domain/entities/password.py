from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class Password:
    id: UUID
    name: str
    encrypted_value: str
    folder: Optional[str] = None

    @classmethod
    def create(
        cls,
        id: UUID,
        name: str,
        encrypted_value: str,
        folder: Optional[str] = None,
    ) -> "Password":
        return cls(
            id=id,
            name=name,
            encrypted_value=encrypted_value,
            folder=folder,
        )
