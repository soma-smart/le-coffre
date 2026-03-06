from dataclasses import dataclass
from uuid import UUID


@dataclass
class Password:
    id: UUID
    name: str
    encrypted_value: str
    folder: str
    login: str | None = None
    url: str | None = None

    @classmethod
    def create(
        cls,
        id: UUID,
        name: str,
        encrypted_value: str,
        folder: str | None,
        login: str | None,
        url: str | None,
    ) -> "Password":
        return cls(
            id=id,
            name=name,
            encrypted_value=encrypted_value,
            folder=folder if folder else "default",
            login=login,
            url=url,
        )
