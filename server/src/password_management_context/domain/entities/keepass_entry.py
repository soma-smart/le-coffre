from dataclasses import dataclass


@dataclass(frozen=True)
class KeepassEntry:
    title: str
    username: str | None
    password: str | None
    url: str | None
    notes: str | None = None
