from dataclasses import dataclass
from uuid import UUID


@dataclass
class Password:
    id: UUID
    name: str
    encrypted_value: str
    folder: str | None = "default"
    login: str | None = None
    url: str | None = None

    def __setattr__(self, name: str, value: object) -> None:
        if name == "folder":
            value = value if value else "default"
        super().__setattr__(name, value)

    @classmethod
    def create(
        cls,
        id: UUID,
        name: str,
        encrypted_value: str,
        folder: str | None = "default",
        login: str | None = None,
        url: str | None = None,
    ) -> "Password":
        return cls(
            id=id,
            name=name,
            encrypted_value=encrypted_value,
            folder=folder,
            login=login,
            url=url,
        )
