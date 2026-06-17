from io import BytesIO

from pykeepass import PyKeePass

from password_management_context.domain.entities.keepass_entry import KeepassEntry


class KeepassReader:
    """Reader responsible for parsing KeePass files."""

    def read_entries(
        self,
        content: bytes,
        master_password: str,
    ) -> list[KeepassEntry]:
        """Read entries from a KeePass file."""
        try:
            keepass = PyKeePass(
                BytesIO(content),
                password=master_password,
            )
        except Exception as e:
            raise ValueError("Fichier KeePass invalide ou mot de passe incorrect") from e

        entries: list[KeepassEntry] = []

        for entry in keepass.entries or []:
            if not entry.title:
                continue

            entries.append(
                KeepassEntry(
                    title=entry.title,
                    username=entry.username,
                    password=entry.password,
                    url=entry.url,
                    notes=entry.notes,
                )
            )

        return entries
