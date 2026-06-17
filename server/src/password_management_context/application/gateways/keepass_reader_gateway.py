from typing import Protocol

from password_management_context.domain.entities.keepass_entry import (
    KeepassEntry,
)


class KeepassReaderGateway(Protocol):
    def read_entries(
        self,
        content: bytes,
        master_password: str,
    ) -> list[KeepassEntry]:
        """Read entries from a KeePass file"""
        ...
